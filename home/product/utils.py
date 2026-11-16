def product_payload(product, *, include_cost=True):
    """داده‌ی کالا برای پاسخ JSON (فرم سریع و جستجوی فاکتور)."""
    payload = {
        "id": product.pk,
        "name": product.name,
        "tag": product.tag,
        "serial_number": product.serial_number,
        "barcode": product.serial_number,
        "unit": product.unit,
        "unit_label": product.get_unit_display(),
        "price_for_customer": str(product.price_for_customer),
        "final_price": str(product.final_price_for_customer()),
        "offer_type": product.offer_type,
        "offer_value": str(product.offer_value),
        "offer_display": product.offer_display,
        "count": product.count,
        "is_active": product.is_active,
    }
    if include_cost:
        payload["price_for_company"] = str(product.price_for_company)
    return payload
