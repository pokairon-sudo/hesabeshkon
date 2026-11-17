from decimal import Decimal, ROUND_HALF_UP

from django.core.validators import MinValueValidator
from django.db import models


class ShopSettings(models.Model):
    """تنظیمات تک‌نمونه‌ای فروشگاه (ردیف شماره ۱)."""

    CURRENCY_TOMAN = "toman"
    CURRENCY_RIAL = "rial"
    CURRENCY_CHOICES = [
        (CURRENCY_TOMAN, "تومان"),
        (CURRENCY_RIAL, "ریال"),
    ]

    shop_name = models.CharField("نام فروشگاه", max_length=120, default="حساب‌شکن")
    phone = models.CharField("تلفن", max_length=30, blank=True, default="")
    address = models.CharField("آدرس", max_length=250, blank=True, default="")

    currency_unit = models.CharField(
        "واحد نمایش قیمت",
        max_length=8,
        choices=CURRENCY_CHOICES,
        default=CURRENCY_TOMAN,
        help_text="قیمت‌ها همیشه به تومان ذخیره می‌شوند؛ این فقط واحد نمایش است.",
    )
    show_usd = models.BooleanField("نمایش معادل دلاری", default=False)
    usd_rate = models.DecimalField(
        "نرخ دلار (تومان)",
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="برای تبدیل نمایشی؛ مثلاً ۹۰٬۰۰۰ تومان.",
    )
    default_markup_percent = models.DecimalField(
        "سود پیش‌فرض کالای جدید (%)",
        max_digits=5,
        decimal_places=2,
        default=Decimal("20"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="هنگام ساخت کالای جدید از روی فاکتور خرید یا OCR استفاده می‌شود.",
    )
    low_stock_threshold = models.PositiveIntegerField(
        "آستانه هشدار موجودی", default=5, help_text="کالاهایی با موجودی کمتر یا مساوی این عدد هشدار می‌گیرند."
    )
    receipt_footer = models.CharField(
        "متن پایین رسید",
        max_length=200,
        blank=True,
        default="از خرید شما سپاسگزاریم 🌿",
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تنظیمات فروشگاه"
        verbose_name_plural = "تنظیمات فروشگاه"

    def __str__(self):
        return self.shop_name

    @classmethod
    def load(cls) -> "ShopSettings":
        """
        تنظیمات را برمی‌گرداند. اگر هنوز ردیفی ساخته نشده باشد، یک نمونه‌ی
        ذخیره‌نشده با مقادیر پیش‌فرض برمی‌گرداند (بدون نوشتن در دیتابیس).
        """
        obj = cls.objects.filter(pk=1).first()
        return obj or cls(pk=1)

    @property
    def currency_label(self) -> str:
        return "ریال" if self.currency_unit == self.CURRENCY_RIAL else "تومان"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)


def round_money(value) -> Decimal:
    if not isinstance(value, Decimal):
        value = Decimal(str(value or 0))
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def format_money(value, shop: ShopSettings | None = None, *, with_unit=True, with_usd=False) -> str:
    """مقدار ذخیره‌شده (تومان) را با واحد/دلار تنظیمات نمایش می‌دهد."""
    shop = shop or ShopSettings.load()
    try:
        amount = Decimal(value or 0)
    except Exception:
        amount = Decimal("0")
    if shop.currency_unit == ShopSettings.CURRENCY_RIAL:
        amount *= 10

    amount = round_money(amount)
    if amount == amount.to_integral():
        number = f"{amount:,.0f}"
    else:
        number = f"{amount:,.2f}"
    result = f"{number} {shop.currency_label}" if with_unit else number

    if with_usd and shop.show_usd and shop.usd_rate and shop.usd_rate > 0:
        usd = (round_money(value) / shop.usd_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        result += f" ≈ ${usd:,.2f}"
    return result
