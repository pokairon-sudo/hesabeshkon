from django.conf import settings
from django.utils import timezone

from .models import ShopSettings


def shop_context(request):
    shop = ShopSettings.load()
    config = {
        "currencyUnit": shop.currency_unit,
        "currencyLabel": shop.currency_label,
        "usdRate": str(shop.usd_rate or 0),
        "showUsd": bool(shop.show_usd),
        "maxInvoiceLines": getattr(settings, "MAX_INVOICE_LINES", 200),
        "maxLineQuantity": getattr(settings, "MAX_LINE_QUANTITY", 100000),
        "shopName": shop.shop_name,
    }
    return {
        "shop": shop,
        "shop_config": config,
        "today": timezone.localdate(),
        "buy_enabled": getattr(settings, "FAKTOR_BUY_ENABLED", True),
    }
