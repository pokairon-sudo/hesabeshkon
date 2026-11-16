from decimal import Decimal, ROUND_HALF_UP

from django.db import models
from django.urls import reverse
from django.utils import timezone

from accounts.models import User


class InvoiceStatus(models.TextChoices):
    DRAFT = "draft", "پیش‌نویس"
    COMPLETED = "completed", "نهایی"


class FaktorSell(models.Model):
    """فاکتور فروش — ابتدا پیش‌نویس، سپس نهایی و ارسال به حسابدار."""

    Status = InvoiceStatus

    number = models.CharField("شماره فاکتور", max_length=30, unique=True, null=True, blank=True)
    date = models.DateField("تاریخ", default=timezone.localdate, db_index=True)
    customer = models.CharField("مشتری", max_length=200, blank=True, default="")
    description = models.TextField("توضیحات", blank=True, default="")

    total_price = models.DecimalField("جمع کل (تومان)", max_digits=16, decimal_places=2, default=Decimal("0"))
    status = models.CharField(
        "وضعیت", max_length=12, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT, db_index=True
    )

    user = models.ForeignKey(User, verbose_name="ثبت‌کننده", on_delete=models.PROTECT, related_name="sells")

    completed_at = models.DateTimeField("زمان نهایی‌سازی", null=True, blank=True)
    accounted = models.BooleanField("ارسال به حسابدار", default=False, db_index=True)
    accounted_at = models.DateTimeField("زمان ارسال به حسابدار", null=True, blank=True)

    created_at = models.DateTimeField("ساخته شد", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین ویرایش", auto_now=True)

    class Meta:
        verbose_name = "فاکتور فروش"
        verbose_name_plural = "فاکتورهای فروش"
        ordering = ["-date", "-id"]
        indexes = [models.Index(fields=["status", "date"])]

    def __str__(self):
        return f"فروش {self.number or self.pk} – {self.customer or 'بدون مشتری'}"

    def save(self, *args, **kwargs):
        if self.number:
            return super().save(*args, **kwargs)
        super().save(*args, **kwargs)
        self.number = f"S-{self.date.year}-{self.pk:05d}"
        super().save(update_fields=["number"])

    def get_absolute_url(self):
        return reverse("faktor:sell-preview", kwargs={"pk": self.pk})

    @property
    def is_draft(self) -> bool:
        return self.status == InvoiceStatus.DRAFT

    @property
    def is_completed(self) -> bool:
        return self.status == InvoiceStatus.COMPLETED

    @property
    def party(self) -> str:
        return self.customer

    def recalc_total(self):
        total = sum((item.total_price for item in self.items.all()), Decimal("0"))
        self.total_price = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.save(update_fields=["total_price", "updated_at"])
        return self.total_price


class FaktorBuy(models.Model):
    """فاکتور خرید — با نهایی‌شدن، موجودی و قیمت خرید کالاها به‌روز می‌شود."""

    Status = InvoiceStatus

    number = models.CharField("شماره فاکتور", max_length=30, unique=True, null=True, blank=True)
    date = models.DateField("تاریخ", default=timezone.localdate, db_index=True)
    supplier = models.CharField("تأمین‌کننده", max_length=200, blank=True, default="")
    description = models.TextField("توضیحات", blank=True, default="")

    total_price = models.DecimalField("جمع کل (تومان)", max_digits=16, decimal_places=2, default=Decimal("0"))
    status = models.CharField(
        "وضعیت", max_length=12, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT, db_index=True
    )

    user = models.ForeignKey(User, verbose_name="ثبت‌کننده", on_delete=models.PROTECT, related_name="buys")

    completed_at = models.DateTimeField("زمان نهایی‌سازی", null=True, blank=True)
    accounted = models.BooleanField("ارسال به حسابدار", default=False, db_index=True)
    accounted_at = models.DateTimeField("زمان ارسال به حسابدار", null=True, blank=True)

    created_at = models.DateTimeField("ساخته شد", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین ویرایش", auto_now=True)

    class Meta:
        verbose_name = "فاکتور خرید"
        verbose_name_plural = "فاکتورهای خرید"
        ordering = ["-date", "-id"]
        indexes = [models.Index(fields=["status", "date"])]

    def __str__(self):
        return f"خرید {self.number or self.pk} – {self.supplier or 'بدون تأمین‌کننده'}"

    def save(self, *args, **kwargs):
        if self.number:
            return super().save(*args, **kwargs)
        super().save(*args, **kwargs)
        self.number = f"B-{self.date.year}-{self.pk:05d}"
        super().save(update_fields=["number"])

    def get_absolute_url(self):
        return reverse("faktor:buy-preview", kwargs={"pk": self.pk})

    @property
    def is_draft(self) -> bool:
        return self.status == InvoiceStatus.DRAFT

    @property
    def is_completed(self) -> bool:
        return self.status == InvoiceStatus.COMPLETED

    @property
    def party(self) -> str:
        return self.supplier

    def recalc_total(self):
        total = sum((item.total_price for item in self.items.all()), Decimal("0"))
        self.total_price = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.save(update_fields=["total_price", "updated_at"])
        return self.total_price


class FaktorItem(models.Model):
    """
    ردیف کالا با «عکس فوری» از نام/بارکد/قیمت خرید تا تاریخچه با حذف کالا از بین نرود.
    هر ردیف دقیقاً به یکی از فاکتور فروش یا خرید تعلق دارد.
    """

    sell = models.ForeignKey(
        FaktorSell, verbose_name="فاکتور فروش", on_delete=models.CASCADE, related_name="items", null=True, blank=True
    )
    buy = models.ForeignKey(
        FaktorBuy, verbose_name="فاکتور خرید", on_delete=models.CASCADE, related_name="items", null=True, blank=True
    )

    product = models.ForeignKey(
        "product.Product", verbose_name="کالا", on_delete=models.SET_NULL, null=True, blank=True
    )
    product_name = models.CharField("نام کالا (عکس فوری)", max_length=200, blank=True, default="")
    barcode = models.CharField("بارکد (عکس فوری)", max_length=100, blank=True, default="")

    quantity = models.PositiveIntegerField("تعداد", default=1)
    unit_price = models.DecimalField("قیمت واحد (تومان)", max_digits=16, decimal_places=2, default=Decimal("0"))
    discount_percent = models.DecimalField(
        "تخفیف ردیف (%)", max_digits=5, decimal_places=2, default=Decimal("0")
    )
    cost_price = models.DecimalField(
        "قیمت خرید واحد (تومان)", max_digits=16, decimal_places=2, default=Decimal("0")
    )

    class Meta:
        verbose_name = "ردیف فاکتور"
        verbose_name_plural = "ردیف‌های فاکتور"
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(sell__isnull=False, buy__isnull=True)
                    | models.Q(sell__isnull=True, buy__isnull=False)
                ),
                name="faktoritem_exactly_one_invoice",
            ),
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="faktoritem_qty_positive"),
        ]

    def __str__(self):
        return f"{self.product_name or (self.product.name if self.product else 'کالا')} × {self.quantity}"

    def save(self, *args, **kwargs):
        if self.product_id:
            if not self.product_name:
                self.product_name = self.product.name
            if not self.barcode:
                self.barcode = self.product.serial_number
        super().save(*args, **kwargs)

    @property
    def total_price(self) -> Decimal:
        discount = self.unit_price * (self.discount_percent / Decimal("100"))
        value = (self.unit_price - discount) * self.quantity
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def profit(self) -> Decimal:
        return (self.total_price - (self.cost_price * self.quantity)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    @property
    def invoice(self):
        return self.sell or self.buy
