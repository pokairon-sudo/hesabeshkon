# home/faktor/management/commands/seed_products.py
# اجرا: python manage.py seed_products

import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from product.models import Product


CATEGORIES = [
    ("لپ‌تاپ", "laptop"),
    ("موبایل", "mobile"),
    ("تبلت", "tablet"),
    ("هدفون", "headphone"),
    ("کیبورد", "keyboard"),
    ("ماوس", "mouse"),
    ("مانیتور", "monitor"),
    ("پرینتر", "printer"),
    ("فلش", "flash"),
    ("هارد", "storage"),
]

BRANDS = [
    "Samsung", "Apple", "LG", "Sony", "Asus",
    "Lenovo", "Dell", "HP", "Xiaomi", "Logitech",
]

OFFER_TYPES = ["percent", "price"]


class Command(BaseCommand):
    help = "ایجاد ۱۰۰ محصول تستی در پایگاه داده"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=100,
            help="تعداد محصولات (پیش‌فرض: ۱۰۰)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="پاک کردن محصولات قبلی قبل از ایجاد",
        )

    def handle(self, *args, **options):
        count = options["count"]

        if options["clear"]:
            deleted, _ = Product.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f"{deleted} محصول قبلی حذف شد.")
            )

        created = 0
        skipped = 0

        for i in range(1, count + 1):
            category_fa, category_en = random.choice(CATEGORIES)
            brand = random.choice(BRANDS)

            name = f"{brand} {category_fa} مدل {random.randint(100, 999)}"
            serial = f"{category_en.upper()}-{brand[:3].upper()}-{i:05d}"
            tag = category_fa

            price_company = Decimal(
                str(random.randint(500_000, 50_000_000))
            )
            # قیمت مشتری ۱۰ تا ۳۰ درصد بالاتر از قیمت شرکت
            markup = Decimal(str(random.uniform(1.10, 1.30)))
            price_customer = (price_company * markup).quantize(Decimal("1"))

            offer_type = random.choice(OFFER_TYPES)
            if offer_type == "percent":
                offer_value = Decimal(str(random.randint(0, 25)))
            else:
                offer_value = Decimal(
                    str(random.randint(0, 2_000_000))
                )

            stock = random.randint(0, 200)

            _, was_created = Product.objects.get_or_create(
                serial_number=serial,
                defaults={
                    "name": name,
                    "tag": tag,
                    "price_for_company": price_company,
                    "price_for_customer": price_customer,
                    "count": stock,
                    "offer_value": offer_value,
                    "offer_type": offer_type,
                },
            )

            if was_created:
                created += 1
            else:
                skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ {created} محصول ایجاد شد."
                + (f" ({skipped} تکراری رد شد)" if skipped else "")
            )
        )

