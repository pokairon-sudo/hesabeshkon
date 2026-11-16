from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "serial_number",
        "tag",
        "unit",
        "price_for_company",
        "price_for_customer",
        "count",
        "offer_display",
        "is_active",
    )
    list_editable = ("price_for_company", "price_for_customer", "count", "is_active")
    list_filter = ("unit", "offer_type", "is_active", "created_at")
    search_fields = ("name", "tag", "serial_number")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")
