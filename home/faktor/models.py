
# faktor/models.py
from django.db import models
from decimal import Decimal
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class FaktorSell(models.Model):
    """فاکتور فروش"""
    # T1.5: human-readable, sequential invoice number (e.g. S-2026-0001).
    # Populated automatically in save() once the row has a pk to build from.
    number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    date        = models.DateField(auto_now_add=True)
    customer    = models.CharField(max_length=200, blank=True)
    total_price = models.DecimalField(max_digits=12,
                                      decimal_places=2,
                                      default=Decimal("0"))
    user        = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField(blank=True)

    class Meta:
        # T1.6: explicit ordering also silences Django's
        # UnorderedObjectListWarning on the paginated list view.
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"فاکتور فروش #{self.number or self.pk} – {self.customer}"

    def get_absolute_url(self):
        return reverse("faktor:sell-edit", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.number:
            year = self.date.year if self.date else timezone.now().year
            self.number = f"S-{year}-{self.pk:04d}"
            super().save(update_fields=["number"])


class FaktorBuy(models.Model):
    """فاکتور خرید"""
    number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    date        = models.DateField(auto_now_add=True)
    # T1.2: blank=True added so a purchase invoice can be created empty and
    # filled in via barcode scan first, then have its supplier set — same
    # workflow FaktorSell already supports for `customer`.
    supplier    = models.CharField(max_length=200, blank=True)
    total_price = models.DecimalField(max_digits=12,
                                      decimal_places=2,
                                      default=Decimal("0"))
    # T1.2/T1.7: nullable so existing rows created before this field never
    # trip a NOT NULL constraint; new invoices always set it in the view.
    user        = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"فاکتور خرید #{self.number or self.pk} – {self.supplier}"

    def get_absolute_url(self):
        return reverse("faktor:buy-edit", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.number:
            year = self.date.year if self.date else timezone.now().year
            self.number = f"B-{year}-{self.pk:04d}"
            super().save(update_fields=["number"])


class FaktorItem(models.Model):
    """
    یک ردیف کالا که می‌تواند به فاکتور فروش یا فاکتور خرید تعلق داشته باشد.
    فقط یکی از دو فیلد `sell` یا `buy` باید مقدار داشته باشد.
    """
    sell = models.ForeignKey(
        FaktorSell,
        on_delete=models.CASCADE,
        related_name="items",
        null=True,
        blank=True,
    )
    buy = models.ForeignKey(
        FaktorBuy,
        on_delete=models.CASCADE,
        related_name="items",
        null=True,
        blank=True,
    )

    product = models.ForeignKey('product.Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    # Bug fix (T4.1 test caught this): same int-vs-Decimal default issue as
    # Product.offer_value — see that field's comment for the full explanation.
    # This is the one that actually crashed FaktorItem.total_price when an
    # item was created directly via FaktorItem.objects.create(...) in a test
    # without an explicit discount_percent and used before a DB round-trip.
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    @property
    def total_price(self):
        discount = self.unit_price * (self.discount_percent / 100)
        return (self.unit_price - discount) * self.quantity

    def __str__(self):
        return f"{self.product.name} × {self.quantity}"
