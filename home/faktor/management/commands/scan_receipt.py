"""خواندن یک فاکتور از خط فرمان و نمایش جدول اعتبارسنجی‌شده.

    python manage.py scan_receipt ~/faktor.jpg
    python manage.py scan_receipt faktor.txt --text --json

هیچ چیزی در دیتابیس نوشته نمی‌شود؛ فقط می‌خواند و گزارش می‌دهد.
"""

import json
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError

from faktor.ocr import OCRInputError, extract_receipt, extract_receipt_from_text
from faktor.receipt import format_report, receipt_summary


class Command(BaseCommand):
    help = "خواندن فاکتور (تصویر یا متن) و نمایش ردیف‌های اعتبارسنجی‌شده"

    def add_arguments(self, parser):
        parser.add_argument("source", help="مسیر فایل تصویر/PDF یا فایل متنی")
        parser.add_argument("--text", action="store_true", help="ورودی یک فایل متنی است، نه تصویر")
        parser.add_argument("--json", action="store_true", help="خروجی JSON به‌جای جدول")

    def handle(self, *args, **options):
        path = Path(options["source"]).expanduser()
        if not path.is_file():
            raise CommandError(f"فایل پیدا نشد: {path}")

        try:
            if options["text"]:
                receipt = extract_receipt_from_text(path.read_text(encoding="utf-8"))
            else:
                upload = SimpleUploadedFile(path.name, path.read_bytes())
                receipt = extract_receipt(upload)
        except OCRInputError as exc:
            raise CommandError(str(exc)) from exc

        if options["json"]:
            payload = receipt_summary(receipt)
            payload["date"] = receipt.date.isoformat() if receipt.date else None
            payload["items"] = [
                {
                    "name": line.name,
                    "weight_kg": float(line.weight) if line.weight is not None else None,
                    "quantity": line.quantity,
                    "unit_price": float(line.unit_price) if line.unit_price is not None else None,
                    "line_total": float(line.line_total) if line.line_total is not None else None,
                    "needs_review": line.needs_review,
                }
                for line in receipt.lines
            ]
            payload.pop("warnings", None)
            payload["warnings"] = receipt.warnings
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
            return

        self.stdout.write(format_report(receipt))
        if receipt.status == "needs_review":
            self.stdout.write(self.style.WARNING("این فاکتور نیاز به بازبینی انسانی دارد."))
        else:
            self.stdout.write(self.style.SUCCESS("حساب‌ها جور است."))
