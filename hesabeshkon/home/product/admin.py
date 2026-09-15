
from django.contrib import admin
from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "tag",
        "serial_number",
        "price_for_company",
        "price_for_customer",
        "count",
        "offer_display",      # custom column
        "offer_value",        # <-- make it visible so it can be editable
        "created_at",
    )

    list_editable = (
        "price_for_company",
        "price_for_customer",
        "count",
        "offer_value",        # now allowed because it's in list_display
    )

    list_filter = ("offer_type", "created_at", "updated_at")
    search_fields = ("name", "tag", "serial_number")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")

    def offer_display(self, obj):
        return f"{obj.offer_value}%" if obj.offer_type == "percent" else f"${obj.offer_value}"
    offer_display.short_description = "Offer"
