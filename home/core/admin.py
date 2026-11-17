from django.contrib import admin

from .models import ShopSettings


@admin.register(ShopSettings)
class ShopSettingsAdmin(admin.ModelAdmin):
    list_display = ("shop_name", "currency_unit", "show_usd", "usd_rate", "updated_at")

    def has_add_permission(self, request):
        return not ShopSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
