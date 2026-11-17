import secrets
from decimal import Decimal, ROUND_HALF_UP

from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse


def _ean13_check_digit(first12: str) -> str:
    total = 0
    for index, char in enumerate(first12):
        digit = int(char)
        total += digit * (1 if index % 2 == 0 else 3)
    return str((10 - total % 10) % 10)


def generate_barcode() -> str:
    """یک بارکد ۱۳ رقمی داخلی (پیشوند ۲۰۰) می‌سازد."""
    for _ in range(50):
        base = "200" + "".join(secrets.choice("0123456789") for _ in range(9))
        code = base + _ean13_check_digit(base)
        if not Product.objects.filter(serial_number=code).exists():
            return code
    raise RuntimeError("ساخت بارکد یکتا ممکن نشد؛ دوباره تلاش کنید.")


class Product(models.Model):
    UNIT_PIECE = "piece"
    UNIT_KG = "kg"
    UNIT_PACK = "pack"
    UNIT_CHOICES = [
        (UNIT_PIECE, "عدد"),
        (UNIT_KG, "کیلوگرم"),
        (UNIT_PACK, "بسته"),
    ]

    name = models.CharField("نام کالا", max_length=200, db_index=True)
    tag = models.CharField("دسته/تگ", max_length=50, blank=True, db_index=True)
    serial_number = models.CharField(
        "بارکد", max_length=100, unique=True, blank=True, help_text="اگر خالی بماند خودکار ساخته می‌شود."
    )
    unit = models.CharField("واحد", max_length=10, choices=UNIT_CHOICES, default=UNIT_PIECE)

    price_for_company = models.DecimalField(
        "قیمت خرید (تومان)",
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    price_for_customer = models.DecimalField(
        "قیمت فروش (تومان)",
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    count = models.PositiveIntegerField("موجودی", default=0)

    offer_value = models.DecimalField(
        "مقدار تخفیف",
        max_digits=14,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    offer_type = models.CharField(
        "نوع تخفیف",
        max_length=7,
        choices=[("percent", "درصدی"), ("price", "مبلغ ثابت")],
        default="percent",
    )

    is_active = models.BooleanField("فعال", default=True)

    created_at = models.DateTimeField("ساخته شد", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین ویرایش", auto_now=True)

    class Meta:
        verbose_name = "کالا"
        verbose_name_plural = "کالاها"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.serial_number})"

    def save(self, *args, **kwargs):
        if not self.serial_number:
            self.serial_number = generate_barcode()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("product:e-product", kwargs={"pk": self.pk})

    # ------------------------------------------------------------------
    # قیمت‌ها
    # ------------------------------------------------------------------
    def final_price_for_customer(self) -> Decimal:
        if self.offer_type == "percent":
            discount = self.price_for_customer * (self.offer_value / Decimal("100"))
        else:
            discount = self.offer_value
        value = self.price_for_customer - discount
        if value < 0:
            value = Decimal("0")
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def discount_amount(self) -> Decimal:
        return (self.price_for_customer - self.final_price_for_customer()).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    @property
    def profit_per_unit(self) -> Decimal:
        return (self.final_price_for_customer() - self.price_for_company).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    @property
    def margin_percent(self) -> Decimal:
        if not self.price_for_company:
            return Decimal("0")
        return ((self.profit_per_unit / self.price_for_company) * Decimal("100")).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )

    @property
    def stock_value(self) -> Decimal:
        return (self.price_for_company * self.count).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def offer_display(self) -> str:
        if not self.offer_value:
            return "—"
        if self.offer_type == "percent":
            return f"{self.offer_value:g}٪"
        return f"{self.offer_value:,.0f} تومان"
