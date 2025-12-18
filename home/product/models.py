from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=200)
    tag = models.CharField(max_length=50, blank=True)
    serial_number = models.CharField(max_length=100, unique=True)

    price_for_company = models.DecimalField(max_digits=10, decimal_places=2)
    price_for_customer = models.DecimalField(max_digits=10, decimal_places=2)

    count = models.PositiveIntegerField(default=0)

    # ---- offer fields -------------------------------------------------
    # numeric value (e.g. 15.0)
    offer_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Discount amount – either a percentage or a fixed price",
    )
    # how to interpret the value: '%' or 'price'
    OFFER_TYPE_CHOICES = [
        ("percent", "Percent %"),
        ("price", "Fixed price"),
    ]
    offer_type = models.CharField(
        max_length=7,
        choices=OFFER_TYPE_CHOICES,
        default="percent",
        help_text="Select whether the offer is a percentage discount or a fixed‑price discount",
    )
    # ------------------------------------------------------------------

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.serial_number})"

    # Helper to calculate the final price for a customer
    def final_price_for_customer(self):
        """Return the price after applying the offer."""
        if self.offer_type == "percent":
            discount = self.price_for_customer * (self.offer_value / 100)
        else:  # price
            discount = self.offer_value
        return max(self.price_for_customer - discount, 0)



