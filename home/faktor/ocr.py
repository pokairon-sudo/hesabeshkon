"""
OCR فاکتور خرید.

از باینری سیستمی tesseract استفاده می‌کند (بدون وابستگی پایتونی سنگین).
اگر بسته‌ی زبان فارسی نصب باشد خودکار «fas+eng» و در غیر این صورت «eng»
استفاده می‌شود. خروجی OCR همیشه در صفحه‌ی بازبینی قابل ویرایش است؛
هیچ داده‌ای بدون تأیید کاربر در دیتابیس نوشته نمی‌شود.
"""

from __future__ import annotations

import mimetypes
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import vision
from .receipt import Receipt, parse_receipt_text, validate

MAX_FILE_SIZE = 12 * 1024 * 1024
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".pdf"}

PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

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
    "فاکتور خرید",
    "تاریخ",
    "شماره",
    "شماره فاکتور",
    "نام کالا",
    "کالا",
    "ردیف",
    "total",
    "subtotal",
    "price",
    "qty",
    "quantity",
    "invoice",
    "tax",
    "discount",
    "cash",
    "change",
    "amount",
    "item",
}

NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
LONG_DIGITS_RE = re.compile(r"\b\d{8,14}\b")


class OCRInputError(ValueError):
    pass


def _tesseract_languages() -> str:
    try:
        output = subprocess.check_output(
            ["tesseract", "--list-langs"], stderr=subprocess.STDOUT, timeout=15, text=True
        )
        languages = {
            line.strip()
            for line in output.splitlines()[1:]
            if line.strip() and " " not in line.strip()
        }
    except (OSError, subprocess.SubprocessError):
        languages = set()
    return "fas+eng" if "fas" in languages else "eng"


def _normalize(text: str) -> str:
    text = text.translate(PERSIAN_DIGITS)
    text = text.replace("٫", ".").replace("،", " ")
    # جداکننده‌ی هزارگان داخل اعداد (50,000) را حذف کن، ولی کاماهای متنی را نگه دار.
    for _ in range(3):
        text = re.sub(r"(?<=\d),(?=\d{3}\b)", "", text)
    return text


def _ocr_image(path: Path) -> str:
    lang = _tesseract_languages()
    try:
        result = subprocess.run(
            [
                "tesseract",
                str(path),
                "stdout",
                "-l",
                lang,
                "--psm",
                "6",
                "-c",
                "preserve_interword_spaces=1",
            ],
            capture_output=True,
            text=True,
            timeout=90,
        )
    except subprocess.TimeoutExpired as exc:
        raise OCRInputError("OCR بیش از حد طول کشید؛ تصویر کوچک‌تری امتحان کنید.") from exc
    if result.returncode != 0:
        raise OCRInputError("خواندن تصویر با Tesseract ممکن نشد.")
    return result.stdout or ""


def _pdf_to_images(path: Path, workdir: Path) -> list[Path]:
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        raise OCRInputError("برای PDF باید بسته‌ی poppler-utils روی سرور نصب باشد.")
    prefix = workdir / "page"
    try:
        subprocess.run(
            [pdftoppm, "-r", "200", "-png", "-f", "1", "-l", "3", str(path), str(prefix)],
            capture_output=True,
            timeout=90,
            check=True,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        raise OCRInputError("تبدیل PDF به تصویر ممکن نشد.") from exc
    return sorted(workdir.glob("page-*.png"))


def _check_upload(uploaded_file) -> str:
    """اعتبارسنجی فایل آپلودی و برگرداندن پسوند."""
    if uploaded_file is None:
        raise OCRInputError("فایلی انتخاب نشده است.")
    if uploaded_file.size > MAX_FILE_SIZE:
        raise OCRInputError("حجم فایل بیشتر از ۱۲ مگابایت است.")
    suffix = Path(uploaded_file.name or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise OCRInputError("فرمت فایل پشتیبانی نمی‌شود (تصویر یا PDF بفرستید).")
    return suffix


def extract_text(uploaded_file) -> tuple[str, list[str]]:
    """فایل آپلودشده را OCR می‌کند و متن خام + هشدارها را برمی‌گرداند."""
    suffix = _check_upload(uploaded_file)
    if not shutil.which("tesseract"):
        raise OCRInputError(
            "Tesseract روی سرور نصب نیست. می‌توانید متن فاکتور را در کادر «متن دستی» جای‌گذاری کنید."
        )

    warnings: list[str] = []
    with tempfile.TemporaryDirectory(prefix="hesab-ocr-") as tmp:
        workdir = Path(tmp)
        source = workdir / f"input{suffix}"
        with open(source, "wb") as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        if suffix == ".pdf":
            images = _pdf_to_images(source, workdir)
            if not images:
                raise OCRInputError("صفحه‌ای در PDF پیدا نشد.")
            texts = [_ocr_image(image) for image in images]
            text = "\n".join(texts)
            if len(images) == 3:
                warnings.append("فقط ۳ صفحه‌ی اول PDF خوانده شد.")
        else:
            text = _ocr_image(source)

    if not text.strip():
        warnings.append("متنی از تصویر خوانده نشد؛ می‌توانید متن را دستی وارد کنید.")
    return text, warnings


# ---------------------------------------------------------------------------
# تبدیل متن خام به ردیف‌های قابل ویرایش
# ---------------------------------------------------------------------------
def _clean_name(text: str) -> str:
    text = NUMBER_RE.sub(" ", text)
    text = re.sub(r"[|;,:\t]+", " ", text)
    text = re.sub(r"[*\-–—•]+", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip(" .-_")


def _is_header(line: str) -> bool:
    normalized = line.strip().lower()
    if not normalized:
        return True
    if normalized in SKIP_WORDS:
        return True
    # سربرگ‌های رایج فاکتور (جمع کل، مبلغ، مالیات، ...)
    if any(normalized.startswith(word + " ") for word in ("جمع", "مبلغ", "تخفیف", "مالیات", "شماره", "تاریخ", "فاکتور")):
        return True
    # خطوطی که تقریباً فقط عدد هستند (شماره فاکتور/تاریخ/تلفن)
    letters = sum(char.isalpha() for char in normalized)
    if letters == 0:
        return True
    return False


def parse_invoice_text(raw_text: str, *, max_rows: int = 100) -> list[dict]:
    """تشخیص ابتکاری ردیف‌ها: نام، بارکد (اختیاری)، تعداد، قیمت واحد."""
    rows: list[dict] = []
    for raw_line in (raw_text or "").splitlines():
        line = _normalize(raw_line).strip()
        if not line or _is_header(line):
            continue

        numbers = NUMBER_RE.findall(line)
        if not numbers:
            continue

        # بارکد: اولین عدد ۸ تا ۱۴ رقمی که در ابتدای خط یا قبل از نام باشد.
        barcode = ""
        barcode_match = LONG_DIGITS_RE.search(line)
        if barcode_match and len(numbers) >= 2:
            barcode = barcode_match.group(0)
            numbers = [n for n in numbers if n != barcode]

        values: list[float] = []
        for number in numbers:
            try:
                values.append(float(number))
            except ValueError:
                continue
        if not values:
            continue

        name = _clean_name(line.replace(barcode, " ") if barcode else line)
        if not name or (len(name) < 2 and not barcode):
            continue
        # اگر نام فقط شامل حروف ناخواناست، رد کن.
        if sum(char.isalpha() for char in name) < 2 and not barcode:
            continue

        qty = 1
        unit_price = 0.0
        if len(values) == 1:
            value = values[0]
            if value <= 100:
                qty = int(value) or 1
                unit_price = 0.0
            else:
                unit_price = value
        elif len(values) == 2:
            first, second = values
            if first <= 10_000 and second >= 100:
                qty, unit_price = int(first) or 1, second
            else:
                qty, unit_price = 1, max(first, second)
        else:
            # حالت رایج: تعداد، قیمت واحد، جمع ردیف
            qty_candidate, unit_candidate, third = values[0], values[1], values[2]
            if (
                qty_candidate <= 100_000
                and unit_candidate >= 0
                and abs(qty_candidate * unit_candidate - third) <= max(third * 0.03, 10)
            ):
                qty, unit_price = int(qty_candidate) or 1, unit_candidate
            else:
                # اگر جمع ردیف در انتها آمده باشد، دو عدد قبلی را بگیر.
                qty, unit_price = int(values[-2]) or 1, values[-1]
                if qty > 100_000:
                    qty = 1

        if qty < 1:
            qty = 1
        if unit_price < 0:
            unit_price = 0
        if unit_price == 0:
            # قیمت صفر تقریباً همیشه یعنی OCR قیمت را نخوانده؛ برای بازبینی علامت بزن.
            needs_review = True
        else:
            needs_review = False

        rows.append(
            {
                "name": name[:200],
                "barcode": barcode,
                "quantity": qty,
                "unit_price": f"{unit_price:.2f}",
                "needs_review": needs_review,
                "raw": raw_line.strip(),
            }
        )
        if len(rows) >= max_rows:
            break
    return rows


def parse_manual_text(text: str) -> tuple[str, list[dict]]:
    text = text or ""
    return text, parse_invoice_text(text)


# ---------------------------------------------------------------------------
# مسیر جدید: مدل بینایی (+ Tesseract به‌عنوان پشتیبان) و اعتبارسنجی حسابی
# ---------------------------------------------------------------------------
def _mime_type(uploaded_file, suffix: str) -> str:
    mime = (getattr(uploaded_file, "content_type", "") or "").split(";")[0].strip().lower()
    if mime == "image/jpg":
        mime = "image/jpeg"
    if mime in vision.SUPPORTED_MIME:
        return mime
    guessed = mimetypes.guess_type(f"upload{suffix}")[0] or ""
    return "image/jpeg" if guessed == "image/jpg" else (guessed or "image/jpeg")


def extract_receipt(uploaded_file) -> Receipt:
    """
    فایل را می‌خواند و فاکتور ساختاریافته‌ی اعتبارسنجی‌شده برمی‌گرداند.

    ترتیب: مدل بینایی (اگر تنظیم شده باشد) → Tesseract → پارس متن + اعتبارسنجی.
    PDF همیشه با Tesseract خوانده می‌شود چون باید اول به تصویر تبدیل شود.
    """
    suffix = _check_upload(uploaded_file)
    warnings: list[str] = []

    if suffix != ".pdf" and vision.is_configured():
        try:
            image_bytes = b"".join(uploaded_file.chunks())
            receipt = vision.extract_receipt(image_bytes, _mime_type(uploaded_file, suffix))
            receipt.warnings.extend(warnings)
            return receipt
        except vision.VisionUnavailable as exc:
            warnings.append(f"مدل بینایی پاسخ نداد ({exc})؛ با Tesseract ادامه داده شد.")

    text, text_warnings = extract_text(uploaded_file)
    warnings.extend(text_warnings)
    receipt = parse_receipt_text(text)
    receipt.warnings.extend(warnings)
    return validate(receipt)


def extract_receipt_from_text(text: str) -> Receipt:
    """مسیر «متن دستی»: همان پارس و همان اعتبارسنجی، بدون OCR."""
    receipt = parse_receipt_text(text or "")
    receipt.provider = "manual"
    return validate(receipt)

