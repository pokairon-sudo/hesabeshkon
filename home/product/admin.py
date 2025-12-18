
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
        "offer_value",        # now allowed because it’s in list_display
    )

    list_filter = ("offer_type", "created_at", "updated_at")
    search_fields = ("name", "tag", "serial_number")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")

    def offer_display(self, obj):
        return f"{obj.offer_value}%" if obj.offer_type == "percent" else f"${obj.offer_value}"
    offer_display.short_description = "Offer"



# from django.contrib import admin
# from .models import Product
#
#
# @admin.register(Product)
# class ProductAdmin(admin.ModelAdmin):
#     # Columns shown in the list view
#     list_display = (
#         "name",
#         "tag",
#         "serial_number",
#         "price_for_company",
#         "price_for_customer",
#         "count",
#         "offer",
#         "created_at",
#     )
#     # Fields you can search by
#     search_fields = ("name", "tag", "serial_number")
#     # Filters on the right side
#     list_filter = ("offer", "created_at", "updated_at")
#     # Make some fields editable directly from the list view
#     list_editable = ("price_for_company", "price_for_customer", "count", "offer")
#     # Order the list view
#     ordering = ("-created_at",)
#
#     # Optional: customize the form layout
#     fieldsets = (
#         (None, {
#             "fields": ("name", "tag", "serial_number")
#         }),
#         ("Pricing", {
#             "fields": ("price_for_company", "price_for_customer")
#         }),
#         ("Inventory", {
#             "fields": ("count", "offer")
#         }),
#         ("Timestamps", {
#             "fields": ("created_at", "updated_at"),
#             "classes": ("collapse",),  # hide by default
#         }),
#     )
#     readonly_fields = ("created_at", "updated_at")
