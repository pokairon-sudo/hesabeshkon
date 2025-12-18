
# faktor/models.py
from django.db import models
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class FaktorSell(models.Model):
    """فاکتور فروش"""
    date        = models.DateField(auto_now_add=True)
    customer    = models.CharField(max_length=200, blank=True)
    total_price = models.DecimalField(max_digits=12,
                                      decimal_places=2,
                                      default=0)
    user        = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"فاکتور فروش #{self.pk} – {self.customer}"

    def get_absolute_url(self):
        return reverse("faktor:sell-edit", kwargs={"pk": self.pk})


class FaktorBuy(models.Model):
    """فاکتور خرید"""
    date        = models.DateField(auto_now_add=True)
    supplier    = models.CharField(max_length=200)
    total_price = models.DecimalField(max_digits=12,
                                      decimal_places=2,
                                      default=0)

    def __str__(self):
        return f"فاکتور خرید #{self.pk} – {self.supplier}"

    def get_absolute_url(self):
        return reverse("faktor:buy-edit", kwargs={"pk": self.pk})


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
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    @property
    def total_price(self):
        discount = self.unit_price * (self.discount_percent / 100)
        return (self.unit_price - discount) * self.quantity

    def __str__(self):
        return f"{self.product.name} × {self.quantity}"
