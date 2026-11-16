"""تست‌های خواندن فاکتور: پارس، اعتبارسنجی حسابی و مسیر وب."""

from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase
from django.urls import reverse

from .receipt import (
    Receipt,
    ReceiptLine,
    build_receipt,
    jalali_to_gregorian,
    money_value,
    parse_date,
    parse_receipt_text,
    receipt_to_rows,
    validate,
    weight_value,
    _split_merged,
)
from .tests import FaktorTestBase

# فاکتور واقعی (میوه‌فروشی) — ارقام فارسی، وزن با اعشار و جداکننده‌ی هزارگان
RECEIPT_TEXT = """حاجی ارزونی
تاریخ: ۱۴۰۴/۰۹/۰۶   ساعت: ۱۳:۱۴:۲۲
شماره فاکتور: ۱۰۷
نام کالا   وزن/تعداد   فی   جمع
لیمو شیرین 0/590 230.000 135.700
خیار شمال 0/760 126.000 95.760
سیب دماوند 1/800 285.000 513.000
نارنگی بج 1/290 230.000 296.700
پرتقال ناول 2/130 295.000 628.350
وزن کل 6/570 kg
جمع کل 1,669,510 تومان
"""


class NumberParsingTests(SimpleTestCase):
    def test_thousand_separators(self):
        self.assertEqual(money_value("۲۳۰.۰۰۰"), Decimal("230000"))
        self.assertEqual(money_value("1,669,510"), Decimal("1669510"))
        self.assertEqual(money_value("513000"), Decimal("513000"))

    def test_weight_formats(self):
        self.assertEqual(weight_value("0/590"), Decimal("0.590"))
        self.assertEqual(weight_value("1/800"), Decimal("1.800"))
        self.assertEqual(weight_value("2/130"), Decimal("2.130"))
        self.assertEqual(weight_value("6/570"), Decimal("6.570"))

    def test_merged_columns_are_rebuilt(self):
        """OCR کلاسیک سه ستون را به «1357002300000590» می‌چسباند."""
        line = _split_merged("1357002300000590")
        self.assertIsNotNone(line)
        self.assertEqual(line.weight, Decimal("0.590"))
        self.assertEqual(line.unit_price, Decimal("230000"))
        self.assertEqual(line.line_total, Decimal("135700"))

    def test_merged_columns_reject_inconsistent_digits(self):
        self.assertIsNone(_split_merged("1234567890123456"))


class DateTests(SimpleTestCase):
    def test_known_jalali_dates(self):
        self.assertEqual(parse_date("۱۴۰۴/۰۹/۰۶"), date(2025, 11, 27))
        self.assertEqual(parse_date("1404-01-01"), date(2025, 3, 21))
        self.assertEqual(jalali_to_gregorian(1403, 1, 1), date(2024, 3, 20))

    def test_unrelated_text(self):
        self.assertIsNone(parse_date("فاکتور شماره ۱۰۷"))


class ReceiptParsingTests(SimpleTestCase):
    def setUp(self):
        self.receipt = validate(parse_receipt_text(RECEIPT_TEXT))

    def test_header_fields(self):
        self.assertEqual(self.receipt.vendor, "حاجی ارزونی")
        self.assertEqual(self.receipt.number, "107")
        self.assertEqual(self.receipt.date, date(2025, 11, 27))

    def test_all_lines_parsed(self):
        names = [line.name for line in self.receipt.lines]
        self.assertEqual(names, ["لیمو شیرین", "خیار شمال", "سیب دماوند", "نارنگی بج", "پرتقال ناول"])

    def test_weighted_lines(self):
        apple = self.receipt.lines[2]
        self.assertEqual(apple.weight, Decimal("1.800"))
        self.assertEqual(apple.unit_price, Decimal("285000"))
        self.assertEqual(apple.line_total, Decimal("513000"))

    def test_totals_reconcile(self):
        self.assertEqual(self.receipt.computed_total, Decimal("1669510"))
        self.assertEqual(self.receipt.printed_total, Decimal("1669510"))
        self.assertEqual(self.receipt.computed_weight, Decimal("6.570"))
        self.assertEqual(self.receipt.status, "ok")
        self.assertTrue(self.receipt.is_weighted)

    def test_rows_are_one_unit_at_line_total(self):
        rows = receipt_to_rows(self.receipt)
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[2]["quantity"], 1)
        self.assertEqual(rows[2]["unit_price"], "513000.00")
        self.assertEqual(rows[2]["weight"], "1.800")
        self.assertFalse(rows[2]["needs_review"])

    def test_quantity_receipt_is_not_weighted(self):
        receipt = validate(parse_receipt_text("قهوه اسپرسو 10 450000 4500000"))
        line = receipt.lines[0]
        self.assertEqual(line.quantity, 10)
        self.assertIsNone(line.weight)
        self.assertEqual(line.unit_price, Decimal("450000"))
        self.assertEqual(receipt.computed_total, Decimal("4500000"))
        self.assertEqual(receipt_to_rows(receipt)[0]["quantity"], 10)


class ValidationTests(SimpleTestCase):
    def test_vision_payload_is_accepted(self):
        payload = {
            "vendor": "حاجی ارزونی",
            "invoice_number": "۱۰۷",
            "date_jalali": "1404/09/06",
            "currency": "تومان",
            "items": [
                {"name": "لیمو شیرین", "weight_kg": 0.59, "unit_price": 230000, "line_total": 135700},
                {"name": "سیب دماوند", "weight_kg": 1.8, "unit_price": 285000, "line_total": 513000},
            ],
            "total": 648700,
            "total_weight_kg": 2.39,
        }
        receipt = validate(build_receipt(payload))
        self.assertEqual(len(receipt.lines), 2)
        self.assertEqual(receipt.computed_total, Decimal("648700"))
        self.assertEqual(receipt.computed_weight, Decimal("2.390"))
        self.assertEqual(receipt.status, "ok")

    def test_times_ten_price_error_is_repaired(self):
        """OCR یک صفر کم می‌خواند: ۲۳٬۰۰۰ به‌جای ۲۳۰٬۰۰۰."""
        receipt = Receipt(
            lines=[ReceiptLine(name="لیمو شیرین", weight=Decimal("0.59"), unit_price=Decimal("23000"), line_total=Decimal("135700"))],
            printed_total=Decimal("135700"),
        )
        receipt = validate(receipt)
        self.assertEqual(receipt.lines[0].unit_price, Decimal("230000"))
        self.assertEqual(receipt.status, "repaired")
        self.assertLess(receipt.confidence, 1.0)
        self.assertTrue(any("اصلاح" in warning for warning in receipt.warnings))

    def test_missing_line_total_is_computed(self):
        receipt = Receipt(
            lines=[ReceiptLine(name="سیب", weight=Decimal("1.8"), unit_price=Decimal("285000"))],
        )
        receipt = validate(receipt)
        self.assertEqual(receipt.lines[0].line_total, Decimal("513000"))
        self.assertEqual(receipt.printed_total, Decimal("513000"))

    def test_total_mismatch_needs_review(self):
        receipt = Receipt(
            lines=[ReceiptLine(name="سیب", weight=Decimal("1.8"), unit_price=Decimal("285000"), line_total=Decimal("513000"))],
            printed_total=Decimal("999999"),
        )
        receipt = validate(receipt)
        self.assertEqual(receipt.status, "needs_review")
        self.assertFalse(receipt.total_matches)
        self.assertTrue(any("یکی نیست" in warning for warning in receipt.warnings))

    def test_unreadable_ocr_is_not_trusted(self):
        """خروجی OCR می‌تواند از نظر حسابی «جور» ولی بی‌معنا باشد."""
        garbage = " اکاک\n D o It Iyl 1 3 3\n B  e شماره فاکتور:-\n"
        receipt = validate(parse_receipt_text(garbage))
        self.assertEqual(receipt.status, "needs_review")
        self.assertFalse(receipt.text_quality_ok)
        self.assertTrue(any("خوانا نیست" in warning or "فارسی" in warning for warning in receipt.warnings))

    def test_clean_receipt_has_text_quality(self):
        receipt = validate(parse_receipt_text(RECEIPT_TEXT))
        self.assertTrue(receipt.text_quality_ok)

    def test_empty_receipt_is_flagged(self):
        receipt = validate(Receipt())
        self.assertEqual(receipt.status, "needs_review")
        self.assertEqual(receipt.confidence, 0.0)


class OCRViewTests(FaktorTestBase):
    def test_manual_text_renders_validation_panel(self):
        response = self.client.post(reverse("faktor:ocr"), {"text": RECEIPT_TEXT})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(len(response.context["rows"]), 5)
        self.assertEqual(response.context["receipt"]["status"], "ok")
        self.assertEqual(response.context["receipt"]["computed_total_display"], "1,669,510")
        self.assertContains(response, "اعتبارسنجی حسابی")

    def test_manual_text_with_broken_total_is_flagged(self):
        broken = RECEIPT_TEXT.replace("جمع کل 1,669,510", "جمع کل 9,999,999")
        response = self.client.post(reverse("faktor:ocr"), {"text": broken})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["receipt"]["status"], "needs_review")
        self.assertContains(response, "نیاز به بازبینی")


class VisionProviderTests(SimpleTestCase):
    """مسیر مدل بینایی بدون شبکه: پاسخ سرویس شبیه‌سازی می‌شود."""

    def test_vision_response_is_validated(self):
        import json
        from unittest import mock

        from django.test import override_settings

        from . import vision

        payload = {
            "vendor": "حاجی ارزونی",
            "invoice_number": "107",
            "date_jalali": "1404/09/06",
            "items": [
                {"name": "لیمو شیرین", "weight_kg": "۰٫۵۹", "unit_price": "230000", "line_total": "135700"},
                {"name": "سیب دماوند", "weight_kg": 1.8, "unit_price": 28500, "line_total": 513000},
            ],
            "total": 648700,
            "total_weight_kg": 2.39,
        }
        response = {"choices": [{"message": {"content": json.dumps(payload, ensure_ascii=False)}}]}

        with override_settings(
            OCR_VISION_BASE_URL="http://vision.local/v1",
            OCR_VISION_API_KEY="test-key",
            OCR_VISION_MODEL="test-model",
        ), mock.patch.object(vision, "_post_json", return_value=response) as post:
            receipt = vision.extract_receipt(b"\xff\xd8\xff", "image/jpeg")

        post.assert_called_once()
        self.assertEqual(receipt.provider, "vision")
        self.assertEqual(receipt.number, "107")
        # ردیف دوم با فی ۲۸٬۵۰۰ اشتباه خوانده شده بود؛ باید ×۱۰ اصلاح شود
        self.assertEqual(receipt.lines[1].unit_price, Decimal("285000"))
        self.assertEqual(receipt.computed_total, Decimal("648700"))
        self.assertEqual(receipt.status, "repaired")

    def test_provider_not_configured_falls_back(self):
        from django.test import override_settings

        from . import vision

        with override_settings(OCR_VISION_API_KEY="", OCR_VISION_MODEL=""):
            self.assertFalse(vision.is_configured())
