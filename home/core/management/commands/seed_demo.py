"""چند کالای نمونه‌ی کافه برای آزمایش سریع."""

from decimal import Decimal

from django.core.management.base import BaseCommand

from product.models import Product


PRODUCTS = [
    ("اسپرسو سینگل", "نوشیدنی گرم", "2000000000017", "45000", "70000", 40),
    ("اسپرسو دوبل", "نوشیدنی گرم", "2000000000024", "60000", "95000", 40),
    ("کاپوچینو", "نوشیدنی گرم", "2000000000031", "70000", "120000", 35),
    ("لاته", "نوشیدنی گرم", "2000000000048", "75000", "130000", 35),
    ("آیس آمریکانو", "نوشیدنی سرد", "2000000000055", "55000", "95000", 25),
    ("چای سبز", "نوشیدنی گرم", "2000000000062", "15000", "35000", 50),
    ("کیک شکلاتی", "دسر", "2000000000079", "90000", "150000", 12),
    ("کروسان", "نان", "2000000000086", "40000", "75000", 18),
    ("آب معدنی", "بسته‌بندی", "2000000000093", "8000", "15000", 60),
    ("دمنوش بهار نارنج", "نوشیدنی گرم", "2000000000109", "25000", "55000", 20),
]


class Command(BaseCommand):
    help = "ساخت کالاهای نمونه کافه"

    def handle(self, *args, **options):
        created = 0
        for name, tag, barcode, buy, sell, count in PRODUCTS:
            _, is_new = Product.objects.get_or_create(
                serial_number=barcode,
                defaults={
                    "name": name,
                    "tag": tag,
                    "price_for_company": Decimal(buy),
                    "price_for_customer": Decimal(sell),
                    "count": count,
                },
            )
            created += int(is_new)
        self.stdout.write(self.style.SUCCESS(f"{created} کالای نمونه ساخته شد."))
