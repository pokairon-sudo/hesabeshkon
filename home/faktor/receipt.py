"""
لایه‌ی «فاکتور خوان» — تبدیل خروجی OCR به ردیف‌های قابل‌اعتماد.

ایده‌ی اصلی: هیچ عددی را باور نکن، مگر با حساب جور دربیاید.
هر ردیف فاکتور وزن‌دار باید در رابطه‌ی  وزن × فی = جمع  صدق کند و مجموع
ردیف‌ها باید با «جمع کل» چاپ‌شده یکی باشد. اگر OCR ستون‌ها را به هم چسبانده
باشد، همین رابطه اجازه می‌دهد رشته‌ی به‌هم‌ریخته را دوباره بشکنیم.

این ماژول عمداً به Django وابسته نیست تا مستقل قابل تست باشد.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

# ---------------------------------------------------------------------------
# نرمال‌سازی متن و اعداد
# ---------------------------------------------------------------------------
_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

#: جداکننده‌های هزارگان که در فاکتورهای ایرانی رایج‌اند: ۲۳۰٬۰۰۰ / 230.000 / 230,000
_THOUSANDS = ("٬", ",", "،", "'", "`")

#: جداکننده‌های اعشار: ۰٫۵۹۰ / 0/590
_DECIMALS = ("٫", "/", "\\")

MONEY_TOLERANCE = Decimal("1")  # یک تومان اختلاف قابل قبول است
WEIGHT_TOLERANCE = Decimal("0.02")  # ۲۰ گرم

#: جمع کل / وزن کل / شماره فاکتور / تاریخ
_TOTAL_LABELS = ("جمع کل", "مبلغ کل", "جمع", "total")
_WEIGHT_LABELS = ("وزن کل", "وزن‌کل", "وزن کل (kg)", "total weight")
_NUMBER_LABELS = ("شماره فاکتور", "شماره فاکتور:", "فاکتور شماره", "invoice")
_DATE_RE = re.compile(r"(1[34]\d{2})\s*[/\-.]\s*(\d{1,2})\s*[/\-.]\s*(\d{1,2})")
_TOKEN_RE = re.compile(r"[0-9][0-9\u066b\u066c.,/\\\u066c]*[0-9]|[0-9]")
_NUMBER_RE = re.compile(r"\d+(?:[.,/]\d+)*")

SKIP_WORDS = {
    "جمع",
    "جمع کل",
    "مبلغ",
    "مبلغ کل",
    "مالیات",
    "تخفیف",
    "تعداد",
    "قیمت",
    "قیمت واحد",
    "فاکتور",
    "تاریخ",
    "ساعت",
    "شماره",
    "شماره فاکتور",
    "نام کالا",
    "کالا",
    "ردیف",
    "وزن",
    "وزن/تعداد",
    "فی",
    "کیلوگرم",
    "kg",
    "total",
    "subtotal",
    "price",
    "qty",
    "invoice",
    "tax",
    "amount",
    "item",
}


class ReceiptError(ValueError):
    """خطای قابل نمایش به کاربر."""


def normalize_digits(text: str) -> str:
    """ارقام فارسی/عربی را به لاتین برمی‌گرداند."""
    return (text or "").translate(_DIGITS)


def normalize_text(text: str) -> str:
    """ی/ک عربی را فارسی می‌کند و فاصله‌های اضافه را جمع می‌کند."""
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace("ي", "ی").replace("ك", "ک").replace("ۀ", "ه")
    text = text.replace("\u200c", " ")  # نیم‌فاصله برای تشخیص سربرگ ساده‌تر است
    return text


def clean_name(text: str) -> str:
    """نام کالا: حذف ارقام و نشانه‌ها، نگه‌داشتن حروف."""
    text = normalize_digits(text)
    text = _NUMBER_RE.sub(" ", text)
    text = re.sub(r"[|;,:\t\-–—•*#]+", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip(" .-_")


def persian_letters(text: str) -> int:
    """تعداد حروف فارسی/عربی یک رشته (برای سنجش خوانایی نام کالا)."""
    return sum(1 for char in (text or "") if "\u0600" <= char <= "\u06ff" and char.isalpha())


def persian_ratio(text: str) -> float:
    """سهم حروف فارسی از متن؛ برای تشخیص OCR بی‌کیفیت."""
    stripped = re.sub(r"\s", "", text or "")
    if not stripped:
        return 0.0
    return persian_letters(stripped) / len(stripped)


@dataclass
class ReceiptLine:
    name: str = ""
    weight: Decimal | None = None
    quantity: int | None = None
    unit_price: Decimal | None = None
    line_total: Decimal | None = None
    raw: str = ""
    flags: list[str] = field(default_factory=list)  # مشکلات حل‌نشده → بازبینی انسانی
    notes: list[str] = field(default_factory=list)  # اصلاح‌های انجام‌شده

    @property
    def is_weighted(self) -> bool:
        return self.weight is not None and self.weight > 0

    @property
    def computed_total(self) -> Decimal | None:
        if self.weight is not None and self.unit_price is not None:
            return (self.weight * self.unit_price).quantize(Decimal("1"))
        if self.quantity is not None and self.unit_price is not None:
            return (Decimal(self.quantity) * self.unit_price).quantize(Decimal("1"))
        return None

    @property
    def needs_review(self) -> bool:
        return bool(self.flags)


@dataclass
class Receipt:
    vendor: str = ""
    number: str = ""
    date: date | None = None
    lines: list[ReceiptLine] = field(default_factory=list)
    printed_total: Decimal | None = None
    printed_weight: Decimal | None = None
    currency: str = "تومان"
    raw_text: str = ""
    provider: str = "manual"
    warnings: list[str] = field(default_factory=list)
    confidence: float = 1.0
    status: str = "ok"  # ok | repaired | needs_review

    @property
    def computed_total(self) -> Decimal:
        total = Decimal("0")
        for line in self.lines:
            value = line.line_total or line.computed_total or Decimal("0")
            total += value
        return total.quantize(Decimal("1"))

    @property
    def computed_weight(self) -> Decimal:
        return sum((line.weight or Decimal("0") for line in self.lines), Decimal("0")).quantize(
            Decimal("0.001")
        )

    @property
    def is_weighted(self) -> bool:
        return any(line.is_weighted for line in self.lines)


# ---------------------------------------------------------------------------
# تفسیر عدد: ۲۳۰.۰۰۰ تومان در برابر ۰/۵۹۰ کیلوگرم
# ---------------------------------------------------------------------------
def _strip_thousands(segment: str) -> str:
    for char in _THOUSANDS:
        segment = segment.replace(char, "")
    return segment


def money_value(segment: str) -> Decimal | None:
    """مقدار پولی را از یک قطعه‌ی متنی می‌خواند (۲۳۰.۰۰۰ → 230000)."""
    raw = _strip_thousands(normalize_digits(segment)).strip()
    if not raw or not raw.replace(".", "").isdigit():
        return None
    if raw.count(".") == 1 and len(raw.split(".")[1]) in (1, 2):
        # اعشار واقعی مثل 45000.50
        try:
            return Decimal(raw)
        except InvalidOperation:
            return None
    value = raw.replace(".", "")
    if not value.isdigit():
        return None
    return Decimal(value)


def weight_value(segment: str) -> Decimal | None:
    """وزن را با اولویت اعشار می‌خواند: 0/590 و 1.800 و 0590 → ۰٫۵۹ و ۱٫۸ و ۰٫۵۹."""
    raw = normalize_digits(segment).strip()
    if not raw:
        return None
    for char in _THOUSANDS:
        raw = raw.replace(char, "")
    for sep in _DECIMALS:
        if sep in raw:
            whole, _, frac = raw.partition(sep)
            if whole.isdigit() and frac.isdigit() and 1 <= len(frac) <= 3:
                return Decimal(f"{whole}.{frac}")
            raw = raw.replace(sep, "")

    if not raw.isdigit():
        digits = re.sub(r"\D", "", raw)
        if not digits:
            return None
        raw = digits

    if len(raw) <= 3:
        value = Decimal(raw)
        return value if value > 0 else None
    if len(raw) == 4 and raw.startswith("0"):
        return Decimal(raw) / Decimal(1000)
    # 1800 → 1.800 ؛ 6570 → 6.570
    return Decimal(raw) / Decimal(1000) if len(raw) <= 6 else None


def _split_merged(digits: str) -> ReceiptLine | None:
    """
    رشته‌ی چسبیده‌ی «۱۳۵۷۰۰۲۳۰۰۰۰۰۵۹۰» را به (جمع، فی، وزن) می‌شکند،
    فقط اگر وزن × فی = جمع دربیاید. این همان جایی است که OCR کلاسیک می‌شکند.
    """
    if not digits.isdigit() or len(digits) < 8:
        return None
    best: tuple[int, ReceiptLine] | None = None
    for i in range(4, len(digits) - 5):
        for j in range(i + 3, len(digits) - 2):
            total_s, price_s, weight_s = digits[:i], digits[i:j], digits[j:]
            total = money_value(total_s)
            price = money_value(price_s)
            weight = weight_value(weight_s)
            if not total or not price or not weight:
                continue
            if not (Decimal("0.01") <= weight <= Decimal("60")):
                continue
            if price < 1000 or total < 1000:
                continue
            if abs(weight * price - total) > MONEY_TOLERANCE:
                continue
            score = 0
            if price % 500 == 0:
                score += 2
            if total % 10 == 0:
                score += 1
            if len(weight_s) == 4 and weight_s.startswith("0"):
                score += 2
            if best is None or score > best[0]:
                best = (score, ReceiptLine(weight=weight, unit_price=price, line_total=total))
    return best[1] if best else None


def _looks_weight(token: str, value: Decimal) -> bool:
    """
    «۱۰» تعداد است یا ۱۰ کیلو؟ فاکتورهای وزنی وزن را با اعشار می‌نویسند
    (۰/۵۹۰ یا 1.800)؛ عدد صحیح کوچک را تعداد می‌گیریم.
    """
    token = normalize_digits(token or "")
    if "/" in token or "٫" in token:
        return True
    if "." in token:
        whole, _, frac = token.partition(".")
        if whole.isdigit() and 1 <= len(frac) <= 3 and int(whole) <= 60:
            return True
    return value != value.to_integral_value()


def _line_from(weight_token: str, weight: Decimal, price: Decimal, total: Decimal) -> ReceiptLine:
    if _looks_weight(weight_token, weight):
        return ReceiptLine(weight=weight, unit_price=price, line_total=total)
    return ReceiptLine(quantity=max(1, int(weight)), unit_price=price, line_total=total)


def _interpret_tokens(tokens: list[str]) -> ReceiptLine | None:
    """
    سه عدد آخر خط را با دو فرض می‌خواند و فرضی را می‌پذیرد که در آن
    وزن × فی = جمع  برقرار باشد (جداکننده‌ی ستون‌ها در OCR قابل اعتماد نیست).
    """
    if not tokens:
        return None
    if len(tokens) == 1:
        merged = re.sub(r"\D", "", normalize_digits(tokens[0]))
        return _split_merged(merged)

    tail = tokens[-3:] if len(tokens) >= 3 else tokens
    if len(tail) < 2:
        return None
    third, second = (tail[-3], tail[-2]) if len(tail) == 3 else (None, tail[-2])
    last = tail[-1]

    # فرض الف: ترتیب چاپی راست‌به‌چپ → جمع، فی، وزن
    weight = weight_value(last)
    price = money_value(second)
    total = money_value(third) if third else None
    if weight and price and total and abs(weight * price - total) <= MONEY_TOLERANCE:
        return _line_from(last, weight, price, total)

    # فرض ب: ترتیب تایپ انسانی چپ‌به‌راست → وزن، فی، جمع
    weight = weight_value(third) if third else None
    price = money_value(second)
    total = money_value(last)
    if weight and price and total and abs(weight * price - total) <= MONEY_TOLERANCE:
        return _line_from(third or "", weight, price, total)

    # هیچ رابطه‌ای برقرار نیست: محتمل‌ترین خوانش را نگه دار و علامت بزن.
    weight = weight_value(last)
    price = money_value(second)
    total = money_value(third) if third else None
    if price and price >= 1000:
        line = ReceiptLine(weight=weight, unit_price=price, line_total=total or (weight or 0) * price)
        line.flags.append("حساب ردیف جور نیست")
        return line
    # حالت بدون وزن: تعداد، فی، جمع
    quantity = weight  # همان تجزیه، ولی «عدد» است
    if price and total and quantity:
        line = ReceiptLine(
            quantity=int(quantity), unit_price=price, line_total=total
        )
        if abs(Decimal(quantity) * price - total) > MONEY_TOLERANCE:
            line.flags.append("حساب ردیف جور نیست")
        return line
    return None


# ---------------------------------------------------------------------------
# خواندن متن خام
# ---------------------------------------------------------------------------
def _is_header(line: str) -> bool:
    normalized = re.sub(r"\s+", " ", line.strip().lower())
    if not normalized:
        return True
    if normalized in SKIP_WORDS:
        return True
    first_word = normalized.split()[0].rstrip(":")
    if first_word in {"تاریخ", "ساعت", "شماره", "فاکتور", "غرفه", "ترازو", "جمع", "مبلغ", "مالیات", "تخفیف"}:
        return True
    if any(normalized.startswith(label + " ") for label in _TOTAL_LABELS + _WEIGHT_LABELS):
        return True
    return False


def _label_number(line: str, labels) -> Decimal | None:
    for label in labels:
        index = line.find(label)
        if index < 0:
            continue
        tail = line[index + len(label):]
        match = _TOKEN_RE.search(normalize_digits(tail))
        if match:
            return money_value(match.group(0))
    return None


def _label_weight(line: str) -> Decimal | None:
    for label in _WEIGHT_LABELS:
        index = line.find(label)
        if index < 0:
            continue
        tail = line[index + len(label):]
        match = _TOKEN_RE.search(normalize_digits(tail))
        if match:
            value = weight_value(match.group(0))
            if value and value > 0:
                return value
    return None


def jalali_to_gregorian(jy: int, jm: int, jd: int) -> date:
    """تبدیل تاریخ شمسی به میلادی (الگوریتم چرخه‌ی ۳۳ساله)."""
    jy += 1595
    days = -355668 + 365 * jy + (jy // 33) * 8 + ((jy % 33) + 3) // 4 + jd
    days += (jm - 1) * 31 if jm < 7 else ((jm - 7) * 30 + 186)
    gy = 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1
    leap = (gy % 4 == 0 and gy % 100 != 0) or gy % 400 == 0
    months = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 0
    while gm < 12 and gd > months[gm]:
        gd -= months[gm]
        gm += 1
    return date(gy, gm + 1, gd)


def parse_date(text: str) -> date | None:
    match = _DATE_RE.search(normalize_digits(text))
    if not match:
        return None
    try:
        jy, jm, jd = (int(part) for part in match.groups())
        if 1300 <= jy <= 1500 and 1 <= jm <= 12 and 1 <= jd <= 31:
            return jalali_to_gregorian(jy, jm, jd)
    except (ValueError, OverflowError):
        return None
    return None


def parse_receipt_text(raw_text: str, *, max_rows: int = 100) -> Receipt:
    """متن OCR (Tesseract) را به فاکتور ساختاریافته تبدیل می‌کند."""
    receipt = Receipt(raw_text=raw_text or "", provider="tesseract")
    receipt.date = parse_date(raw_text)

    for raw_line in (raw_text or "").splitlines():
        line = normalize_text(raw_line).strip()
        if not line:
            continue
        if _is_header(line):
            total = _label_number(line, _TOTAL_LABELS)
            if total and total > 0:
                receipt.printed_total = total
            weight = _label_weight(line)
            if weight:
                receipt.printed_weight = weight
            if any(label in line for label in _NUMBER_LABELS):
                number = _label_number(line, _NUMBER_LABELS)
                if number:
                    receipt.number = str(int(number))
            continue
        if any(label in line for label in _NUMBER_LABELS):
            number = _label_number(line, _NUMBER_LABELS)
            if number:
                receipt.number = str(int(number))
            continue
        if not receipt.vendor and not any(char.isdigit() for char in line):
            name = clean_name(line)
            if sum(char.isalpha() for char in name) >= 3:
                receipt.vendor = name[:200]
                continue

        tokens = [token for token in _TOKEN_RE.findall(normalize_digits(line)) if any(c.isdigit() for c in token)]
        if not tokens:
            continue
        parsed = _interpret_tokens(tokens)
        if parsed is None:
            continue
        parsed.raw = raw_line.strip()
        parsed.name = clean_name(line)[:200]
        if not parsed.name:
            continue
        receipt.lines.append(parsed)
        if len(receipt.lines) >= max_rows:
            break
    return receipt


# ---------------------------------------------------------------------------
# ورودی ساختاریافته (مدل بینایی)
# ---------------------------------------------------------------------------
def _to_decimal(value) -> Decimal | None:
    if value in (None, "", "-"):
        return None
    try:
        return Decimal(str(value).replace("٬", "").replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None


def build_receipt(payload: dict, *, raw_text: str = "", provider: str = "vision") -> Receipt:
    """JSON مدل بینایی را به Receipt تبدیل می‌کند (بدون اعتماد به صحت اعداد)."""
    if not isinstance(payload, dict):
        raise ReceiptError("خروجی OCR ساختار معتبری ندارد.")

    receipt = Receipt(raw_text=raw_text, provider=provider)
    receipt.vendor = str(payload.get("vendor") or "").strip()[:200]
    receipt.number = str(payload.get("invoice_number") or "").strip()[:30]
    receipt.printed_total = _to_decimal(payload.get("total"))
    receipt.printed_weight = _to_decimal(payload.get("total_weight_kg"))

    date_text = payload.get("date_jalali") or payload.get("date")
    receipt.date = parse_date(str(date_text)) if date_text else None

    items = payload.get("items") or []
    if not isinstance(items, list):
        raise ReceiptError("فهرست اقلام در خروجی OCR معتبر نیست.")

    for item in items[:100]:
        if not isinstance(item, dict):
            continue
        line = ReceiptLine(
            name=str(item.get("name") or "").strip()[:200],
            weight=_to_decimal(item.get("weight_kg")),
            unit_price=_to_decimal(item.get("unit_price")),
            line_total=_to_decimal(item.get("line_total")),
            raw=str(item.get("raw") or "")[:300],
        )
        quantity = item.get("quantity")
        if quantity not in (None, "", 0) and line.weight is None:
            try:
                line.quantity = max(1, int(float(quantity)))
            except (TypeError, ValueError):
                line.quantity = None
        if not line.name and line.line_total is None:
            continue
        receipt.lines.append(line)
    return receipt


# ---------------------------------------------------------------------------
# اعتبارسنجی: تنها داور واقعی، حساب است
# ---------------------------------------------------------------------------
def validate(receipt: Receipt) -> Receipt:
    """
    هر ردیف را بازمحاسبه می‌کند، خطاهای ×۱۰ را اصلاح می‌کند و مجموع را با
    «جمع کل» چاپ‌شده مقایسه می‌کند. خروجی همان Receipt با warnings و confidence.
    """
    repairs = 0
    for line in receipt.lines:
        if line.unit_price is None:
            line.flags.append("فی خوانده نشد")
            continue

        expected = line.computed_total
        if line.line_total is None:
            if expected is not None:
                line.line_total = expected
                line.notes.append("جمع ردیف از فی و وزن محاسبه شد")
                repairs += 1
            continue

        if expected is None:
            continue
        if abs(expected - line.line_total) <= MONEY_TOLERANCE:
            continue

        # خطای رایج OCR: یک صفر کم یا زیاد در فی/جمع
        for factor in (Decimal(10), Decimal("0.1")):
            if abs(expected * factor - line.line_total) <= MONEY_TOLERANCE:
                line.unit_price = (line.unit_price * factor).quantize(Decimal("1"))
                line.notes.append("فی با جمع ردیف اصلاح شد (خطای ×۱۰)")
                repairs += 1
                break
        else:
            line.line_total = expected
            line.notes.append("جمع ردیف با فی × وزن بازنویسی شد")
            repairs += 1

    computed = receipt.computed_total
    if receipt.printed_total is not None:
        if abs(computed - receipt.printed_total) > MONEY_TOLERANCE:
            for factor in (Decimal(10), Decimal("0.1")):
                if abs(computed * factor - receipt.printed_total) <= MONEY_TOLERANCE:
                    receipt.warnings.append(
                        "مجموع ردیف‌ها با «جمع کل» چاپ‌شده ۱۰ برابر اختلاف دارد؛ جمع کل اصلاح شد."
                    )
                    receipt.printed_total = computed
                    repairs += 1
                    break
            else:
                receipt.warnings.append(
                    f"مجموع ردیف‌ها ({computed:,}) با جمع کل چاپ‌شده ({receipt.printed_total:,}) یکی نیست."
                )
        receipt.total_matches = abs(computed - receipt.printed_total) <= MONEY_TOLERANCE
    else:
        receipt.printed_total = computed
        receipt.total_matches = True

    if receipt.printed_weight is not None and receipt.is_weighted:
        if abs(receipt.computed_weight - receipt.printed_weight) > WEIGHT_TOLERANCE:
            receipt.warnings.append(
                f"مجموع وزن ({receipt.computed_weight} kg) با وزن کل چاپ‌شده "
                f"({receipt.printed_weight} kg) یکی نیست."
            )

    for line in receipt.lines:
        if (line.flags or line.notes) and line.name:
            receipt.warnings.append(f"ردیف «{line.name}»: {'؛ '.join(line.flags + line.notes)}")

    # دروازه‌ی کیفیت: خروجی OCR ممکن است از نظر داخلی «جور» باشد ولی نام کالا
    # و ارقام کاملاً بی‌معنا باشند (تصویر تار یا خوانده‌نشده).
    quality_ok = True
    if receipt.lines and not any(persian_letters(line.name) >= 2 for line in receipt.lines):
        quality_ok = False
        receipt.warnings.append(
            "نام کالاها خوانا نیست؛ به نظر می‌رسد OCR کیفیت کافی نداشته. عکس واضح‌تر یا مدل بینایی را امتحان کنید."
        )
    if receipt.provider == "tesseract" and receipt.raw_text and persian_ratio(receipt.raw_text) < 0.15:
        quality_ok = False
        receipt.warnings.append(
            "متن خوانده‌شده تقریباً هیچ حرف فارسی ندارد؛ احتمالاً تصویر تار، کج یا کم‌نور است."
        )
    receipt.text_quality_ok = quality_ok

    review = sum(1 for line in receipt.lines if line.needs_review)
    total_mismatch = getattr(receipt, "total_matches", True) is False
    if not receipt.lines:
        receipt.status = "needs_review"
        receipt.confidence = 0.0
    elif review or total_mismatch or not quality_ok:
        receipt.status = "needs_review"
        penalty = 0.4 * review / max(1, len(receipt.lines))
        penalty += 0.3 if total_mismatch else 0
        penalty += 0.65 if not quality_ok else 0
        receipt.confidence = max(0.05, 1 - penalty)
    elif repairs or receipt.warnings:
        receipt.status = "repaired"
        receipt.confidence = max(0.3, 0.85 - 0.05 * repairs)
    else:
        receipt.status = "ok"
        receipt.confidence = 1.0
    return receipt


def receipt_to_rows(receipt: Receipt) -> list[dict]:
    """
    تبدیل به شکل ردیف‌های فرم بازبینی.

    ردیف وزنی در دیتابیس یک «بسته» است: تعداد ۱ و قیمت = جمع ردیف،
    تا جمع فاکتور و موجودی با همان مبالغ چاپ‌شده جور باشد.
    """
    rows: list[dict] = []
    for line in receipt.lines:
        if line.is_weighted and line.line_total is not None:
            quantity = 1
            unit_price = line.line_total
        else:
            quantity = line.quantity or 1
            unit_price = line.unit_price or line.line_total or Decimal("0")
        rows.append(
            {
                "name": line.name,
                "barcode": "",
                "quantity": quantity,
                "unit_price": f"{Decimal(unit_price):.2f}",
                "weight": f"{line.weight:.3f}" if line.weight is not None else "",
                "needs_review": line.needs_review or unit_price <= 0,
                "raw": line.raw,
            }
        )
    return rows


def receipt_summary(receipt: Receipt) -> dict:
    """خلاصه‌ی قابل نمایش در قالب."""
    computed = receipt.computed_total
    printed = receipt.printed_total
    return {
        "vendor": receipt.vendor,
        "number": receipt.number,
        "date": receipt.date,
        "provider": receipt.provider,
        "status": receipt.status,
        "confidence": round(receipt.confidence * 100),
        "lines": len(receipt.lines),
        "computed_total": computed,
        "computed_total_display": f"{computed:,.0f}",
        "printed_total": printed,
        "printed_total_display": f"{printed:,.0f}" if printed is not None else "",
        "total_matches": getattr(receipt, "total_matches", None),
        "computed_weight": receipt.computed_weight,
        "printed_weight": receipt.printed_weight,
        "is_weighted": receipt.is_weighted,
        "quality": getattr(receipt, "text_quality_ok", True),
        "warnings": receipt.warnings,
    }


def format_report(receipt: Receipt) -> str:
    """جدول متنی برای خروجی خط فرمان."""
    summary = receipt_summary(receipt)
    lines = [
        f"فروشنده: {summary['vendor'] or '—'}   فاکتور: {summary['number'] or '—'}"
        f"   تاریخ: {summary['date'] or '—'}   منبع: {summary['provider']}",
        "",
        f"{'#':>2}  {'نام کالا':<28} {'وزن':>7} {'فی':>12} {'جمع':>12}",
        "-" * 70,
    ]
    for index, line in enumerate(receipt.lines, start=1):
        weight = f"{line.weight:.3f}" if line.weight is not None else "—"
        price = f"{line.unit_price:,.0f}" if line.unit_price is not None else "—"
        total = f"{line.line_total:,.0f}" if line.line_total is not None else "—"
        lines.append(f"{index:>2}  {line.name[:28]:<28} {weight:>7} {price:>12} {total:>12}")
    lines += [
        "-" * 70,
        f"جمع: {receipt.computed_total:,} {receipt.currency}"
        f"   وزن: {receipt.computed_weight} kg"
        f"   اطمینان: {summary['confidence']}٪ ({receipt.status})",
    ]
    for warning in receipt.warnings:
        lines.append(f"⚠ {warning}")
    return "\n".join(lines)
