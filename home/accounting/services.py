import logging

from django.db import OperationalError, transaction
from django.utils import timezone

from .models import AccountantInvoice, AccountantItem

ALIAS = "accountant"
logger = logging.getLogger("accounting")


class AccountantUnavailable(RuntimeError):
    """دیتابیس حسابدار در دسترس نیست (مثلاً migrate روی آن اجرا نشده)."""


def _check(_exc: Exception) -> None:
    raise AccountantUnavailable(
        "دیتابیس حسابدار آماده نیست. دستور «python manage.py migrate --database=accountant» را اجرا کنید."
    ) from _exc


def is_available() -> bool:
    try:
        AccountantInvoice.objects.using(ALIAS).exists()
        return True
    except Exception:  # noqa: BLE001
        return False


def _build(invoice, kind: str):
    is_sell = kind == AccountantInvoice.KIND_SELL
    source_id = invoice.pk
    defaults = {
        "kind": kind,
        "source_id": source_id,
        "number": invoice.number or f"{(kind[0]).upper()}-{source_id}",
        "date": invoice.date,
        "party": (invoice.customer if is_sell else invoice.supplier) or "",
        "total": invoice.total_price,
        "status": AccountantInvoice.STATUS_POSTED,
        "note": invoice.description or "",
    }
    items = []
    for item in invoice.items.all():
        items.append(
            {
                "product_name": item.product_name,
                "barcode": item.barcode,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "discount_percent": item.discount_percent,
                "cost_price": item.cost_price,
                "line_total": item.total_price,
            }
        )
    return defaults, items


def _post(invoice, kind: str):
    defaults, items = _build(invoice, kind)
    try:
        with transaction.atomic(using=ALIAS):
            obj, created = AccountantInvoice.objects.using(ALIAS).update_or_create(
                kind=kind,
                source_id=invoice.pk,
                defaults=defaults,
            )
            # هر بار ارسال، ردیف‌ها آینه‌ی فاکتور اصلی می‌شوند (idempotent).
            AccountantItem.objects.using(ALIAS).filter(invoice=obj).delete()
            AccountantItem.objects.using(ALIAS).bulk_create(
                [AccountantItem(invoice=obj, **row) for row in items]
            )
    except OperationalError as exc:
        _check(exc)
    except AccountantUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("accountant sync failed for %s %s", kind, invoice.pk)
        raise AccountantUnavailable(str(exc)) from exc

    # علامت‌گذاری در دیتابیس اصلی
    model = type(invoice)
    model.objects.filter(pk=invoice.pk).update(accounted=True, accounted_at=timezone.now())
    invoice.accounted = True
    invoice.accounted_at = timezone.now()
    return obj


def post_sell(invoice):
    return _post(invoice, AccountantInvoice.KIND_SELL)


def post_buy(invoice):
    return _post(invoice, AccountantInvoice.KIND_BUY)


def void(kind: str, source_id: int) -> None:
    """فاکتور حسابدار را ابطال می‌کند (حذف نمی‌کند تا سابقه بماند)."""
    try:
        AccountantInvoice.objects.using(ALIAS).filter(kind=kind, source_id=source_id).update(
            status=AccountantInvoice.STATUS_VOID, updated_at=timezone.now()
        )
    except OperationalError as exc:
        logger.warning("accountant db unavailable while voiding %s %s", kind, source_id)
        _check(exc)
