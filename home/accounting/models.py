from django.db import models


class AccountantInvoice(models.Model):
    """
    تصویر تغییرناپذیر فاکتور در دیتابیس جداگانه‌ی حسابدار.
    هیچ کلید خارجی‌ای به دیتابیس اصلی ندارد تا دو دیتابیس مستقل بمانند.
    """

    KIND_SELL = "sell"
    KIND_BUY = "buy"
    KIND_CHOICES = [(KIND_SELL, "فروش"), (KIND_BUY, "خرید")]

    STATUS_POSTED = "posted"
    STATUS_VOID = "void"
    STATUS_CHOICES = [(STATUS_POSTED, "ثبت‌شده"), (STATUS_VOID, "ابطال‌شده")]

    kind = models.CharField(max_length=8, choices=KIND_CHOICES)
    source_id = models.PositiveBigIntegerField()
    number = models.CharField(max_length=30, unique=True)
    date = models.DateField()
    party = models.CharField(max_length=200, blank=True)
    total = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_POSTED)
    note = models.TextField(blank=True)
    posted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "فاکتور حسابدار"
        verbose_name_plural = "فاکتورهای حسابدار"
        ordering = ["-date", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["kind", "source_id"], name="uniq_accountant_source")
        ]

    def __str__(self):
        return f"{self.get_kind_display()} {self.number} – {self.party}"


class AccountantItem(models.Model):
    invoice = models.ForeignKey(AccountantInvoice, on_delete=models.CASCADE, related_name="items")
    product_name = models.CharField(max_length=200)
    barcode = models.CharField(max_length=100, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cost_price = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=16, decimal_places=2, default=0)

    class Meta:
        verbose_name = "ردیف حسابدار"
        verbose_name_plural = "ردیف‌های حسابدار"

    def __str__(self):
        return f"{self.product_name} × {self.quantity}"
