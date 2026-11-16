"""
خواندن فاکتور با «مدل بینایی» (VLM).

چرا؟ OCR کلاسیک (Tesseract) روی فاکتور حرارتی فارسی، ستون‌ها را به هم
می‌چسباند و نام کالا را نابود می‌کند. مدل بینایی چیدمان و زمینه را می‌فهمد،
ولی ممکن است رقم را با اطمینان اشتباه بخواند؛ به همین دلیل خروجی این ماژول
هرگز مستقیم ذخیره نمی‌شود و همیشه از فیلتر `receipt.validate` می‌گذرد.

سازگار با هر سرویس OpenAI-compatible (OpenAI, OpenRouter, vLLM, Ollama,
LM Studio, ...) — فقط base_url و model را در تنظیمات بگذارید.
بدون وابستگی پایتونی اضافه: urllib از کتابخانه‌ی استاندارد.
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request

from django.conf import settings

from .receipt import ReceiptError, build_receipt, validate

PROMPT = """این تصویر یک فاکتور فروشگاه (معمولاً میوه‌فروشی یا سوپرمارکت ایرانی) است.
متن را دقیق بخوان و فقط یک شیء JSON برگردان؛ هیچ توضیحی ننویس.

قواعد:
- ارقام را همیشه لاتین بنویس (۰۱۲۳ → 0123).
- نقطه و کاما در اعداد، جداکننده‌ی هزارگان است: ۲۳۰.۰۰۰ یعنی 230000.
- وزن را به کیلوگرم و با اعشار بنویس: «۰/۵۹۰» یعنی 0.59 و «۱/۸۰۰» یعنی 1.8.
- اگر ردیفی تعداد دارد نه وزن، weight_kg را null و quantity را عدد بگذار.
- فی = قیمت هر کیلوگرم (یا هر واحد)، و line_total = جمع همان ردیف.
- جمع کل و وزن کل چاپ‌شده را جدا برگردان.
- اگر چیزی خوانا نیست null بگذار؛ حدس نزن و عدد از خودت نساز.
- تاریخ شمسی را به شکل YYYY/MM/DD برگردان.

ساختار:
{
  "vendor": "نام فروشگاه",
  "invoice_number": "۱۰۷",
  "date_jalali": "1404/09/06",
  "currency": "تومان",
  "items": [
    {"name": "لیمو شیرین", "weight_kg": 0.59, "quantity": null,
     "unit_price": 230000, "line_total": 135700}
  ],
  "total": 1669510,
  "total_weight_kg": 6.57
}"""

SUPPORTED_MIME = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/bmp",
    "image/tiff",
}


class VisionUnavailable(ReceiptError):
    """سرویس بینایی تنظیم نشده یا در دسترس نیست (باید به Tesseract برگردیم)."""


def _config() -> dict:
    return {
        "base_url": (getattr(settings, "OCR_VISION_BASE_URL", "") or "").rstrip("/"),
        "api_key": getattr(settings, "OCR_VISION_API_KEY", "") or "",
        "model": getattr(settings, "OCR_VISION_MODEL", "") or "",
        "timeout": int(getattr(settings, "OCR_VISION_TIMEOUT", 90) or 90),
    }


def is_configured() -> bool:
    config = _config()
    return bool(config["api_key"] and config["model"] and config["base_url"])


def _post_json(url: str, payload: dict, api_key: str, timeout: int) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise VisionUnavailable(f"سرویس OCR خطا داد ({exc.code}): {detail}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise VisionUnavailable("ارتباط با سرویس OCR برقرار نشد.") from exc
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise VisionUnavailable("پاسخ سرویس OCR JSON معتبر نبود.") from exc


def _content_text(response: dict) -> str:
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise VisionUnavailable("پاسخ سرویس OCR ساختار مورد انتظار را نداشت.") from exc
    if isinstance(content, list):  # بعضی سرویس‌ها بلوک متنی برمی‌گردانند
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    return str(content or "")


def _parse_json_object(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[1] if "\n" in text else text
        text = text.removeprefix("json").strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise VisionUnavailable("مدل بینایی JSON برنگرداند.")
    try:
        data = json.loads(text[start : end + 1])
    except ValueError as exc:
        raise VisionUnavailable("JSON مدل بینایی قابل خواندن نبود.") from exc
    if not isinstance(data, dict):
        raise VisionUnavailable("خروجی مدل بینایی شیء JSON نبود.")
    return data


def extract_receipt(image_bytes: bytes, mime_type: str = "image/jpeg"):
    """
    تصویر را به Receipt تبدیل می‌کند.

    خروجی همیشه از `receipt.validate` گذشته است: یعنی اعداد با رابطه‌ی
    وزن × فی = جمع و مجموع ردیف‌ها سنجیده شده‌اند.
    """
    config = _config()
    if not is_configured():
        raise VisionUnavailable(
            "مدل بینایی تنظیم نشده است (OCR_VISION_API_KEY / OCR_VISION_MODEL)."
        )
    if mime_type not in SUPPORTED_MIME:
        raise VisionUnavailable(f"فرمت {mime_type} برای مدل بینایی پشتیبانی نمی‌شود.")

    encoded = base64.b64encode(image_bytes).decode("ascii")
    payload = {
        "model": config["model"],
        "temperature": 0,
        "max_tokens": 3000,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "تو یک استخراج‌کننده‌ی دقیق داده از تصویر فاکتور هستی و فقط JSON برمی‌گردانی."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{encoded}", "detail": "high"},
                    },
                ],
            },
        ],
    }
    response = _post_json(f"{config['base_url']}/chat/completions", payload, config["api_key"], config["timeout"])
    data = _parse_json_object(_content_text(response))
    receipt = build_receipt(data, raw_text=json.dumps(data, ensure_ascii=False, indent=2), provider="vision")
    return validate(receipt)
