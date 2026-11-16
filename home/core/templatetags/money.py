from decimal import Decimal, InvalidOperation

from django import template

from core.models import ShopSettings, format_money, round_money

register = template.Library()


@register.filter
def money(value, shop=None):
    """مبلغ ذخیره‌شده (تومان) را با واحد نمایش می‌دهد."""
    return format_money(value, shop if isinstance(shop, ShopSettings) else None)


@register.filter
def money_usd(value, shop=None):
    """مبلغ همراه با معادل دلاری (اگر در تنظیمات فعال باشد)."""
    return format_money(
        value, shop if isinstance(shop, ShopSettings) else None, with_usd=True
    )


@register.filter
def money_short(value, shop=None):
    """فقط عدد قالب‌بندی‌شده، بدون واحد."""
    return format_money(
        value, shop if isinstance(shop, ShopSettings) else None, with_unit=False, with_usd=False
    )


@register.filter
def usd(value, shop=None):
    shop = shop if isinstance(shop, ShopSettings) else ShopSettings.load()
    try:
        amount = Decimal(value or 0)
        rate = Decimal(shop.usd_rate or 0)
    except (InvalidOperation, TypeError):
        return "—"
    if rate <= 0:
        return "—"
    return f"${(round_money(amount) / rate):,.2f}"


@register.filter
def pct(value):
    try:
        return f"{Decimal(value):,.1f}%"
    except (InvalidOperation, TypeError):
        return "—"


@register.filter
def fa_digits(value):
    """تبدیل ارقام لاتین به فارسی برای متن‌های غیرعددی/نمایشی."""
    table = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    return str(value).translate(table)
