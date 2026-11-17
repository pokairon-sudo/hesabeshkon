from django.contrib import admin

from .models import FaktorBuy, FaktorItem, FaktorSell


class FaktorItemInline(admin.TabularInline):
    model = FaktorItem
    extra = 0
    fields = ("product", "product_name", "barcode", "quantity", "unit_price", "cost_price")
    readonly_fields = ("product_name", "barcode")


@admin.register(FaktorSell)
class FaktorSellAdmin(admin.ModelAdmin):
    list_display = ("number", "date", "customer", "total_price", "status", "accounted", "user")
    list_filter = ("status", "accounted", "date")
    search_fields = ("number", "customer")
    readonly_fields = ("number", "completed_at", "accounted_at", "created_at", "updated_at")
    inlines = [FaktorItemInline]


@admin.register(FaktorBuy)
class FaktorBuyAdmin(admin.ModelAdmin):
    list_display = ("number", "date", "supplier", "total_price", "status", "accounted", "user")
    list_filter = ("status", "accounted", "date")
    search_fields = ("number", "supplier")
    readonly_fields = ("number", "completed_at", "accounted_at", "created_at", "updated_at")
    inlines = [FaktorItemInline]


@admin.register(FaktorItem)
class FaktorItemAdmin(admin.ModelAdmin):
    list_display = ("product_name", "barcode", "quantity", "unit_price", "cost_price", "sell", "buy")
    search_fields = ("product_name", "barcode")
