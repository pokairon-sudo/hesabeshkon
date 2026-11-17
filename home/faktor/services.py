from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from accounting.models import AccountantInvoice
from accounting.services import AccountantUnavailable, post_buy, post_sell, void as void_accountant
from core.models import ShopSettings
from product.models import Product

from .models import FaktorBuy, FaktorItem, FaktorSell, InvoiceStatus


class InvoiceError(ValueError):
    """خطای قابل نمایش به کاربر."""


class StockError(InvoiceError):
    pass


# ---------------------------------------------------------------------------
# ساخت پیش‌نویس از سبد خرید (سمت سرور، قیمت‌ها قابل اعتماد نیستند)
# ---------------------------------------------------------------------------
def clean_quantity(value) -> int:
    try:
        qty = int(value)
    except (TypeError, ValueError):
        raise InvoiceError("تعداد نامعتبر است.")
    if qty < 1:
        raise InvoiceError("تعداد باید حداقل ۱ باشد.")
    return qty


def clean_price(value) -> Decimal:
    try:
        price = Decimal(str(value if value not in (None, "") else "0"))
    except (InvalidOperation, TypeError, ValueError):
        raise InvoiceError("قیمت نامعتبر است.")
    if price < 0:
        raise InvoiceError("قیمت نمی‌تواند منفی باشد.")
    return price.quantize(Decimal("0.01"))


def _lock_draft(invoice, model):
    obj = model.objects.select_for_update().get(pk=invoice.pk)
    if obj.status != InvoiceStatus.DRAFT:
        raise InvoiceError("فاکتور نهایی‌شده قابل ویرایش نیست.")
    return obj


def save_sell_from_cart(*, invoice, lines, customer, description, user):
    """سبد فروش را در یک پیش‌نویس ذخیره می‌کند (موجودی را تغییر نمی‌دهد)."""
    if not lines:
        raise InvoiceError("حداقل یک کالا به فاکتور اضافه کنید.")
    with transaction.atomic():
        if invoice is None:
            invoice = FaktorSell.objects.create(user=user)
        else:
            invoice = _lock_draft(invoice, FaktorSell)

        invoice.customer = (customer or "").strip()[:200]
        invoice.description = (description or "").strip()
        invoice.save(update_fields=["customer", "description", "updated_at"])

        invoice.items.all().delete()
        total = Decimal("0")
        for line in lines:
            product = line["product"]
            qty = line["quantity"]
            item = FaktorItem(
                sell=invoice,
                product=product,
                product_name=product.name,
                barcode=product.serial_number,
                quantity=qty,
                unit_price=product.final_price_for_customer(),
                cost_price=product.price_for_company,
            )
            item.save()
            total += item.total_price

        invoice.total_price = total.quantize(Decimal("0.01"))
        invoice.save(update_fields=["total_price", "updated_at"])
    return invoice


def save_buy_from_cart(*, invoice, lines, supplier, description, user):
    """سبد خرید را در یک پیش‌نویس ذخیره می‌کند؛ قیمت خرید از کاربر پذیرفته می‌شود."""
    if not lines:
        raise InvoiceError("حداقل یک کالا به فاکتور اضافه کنید.")
    with transaction.atomic():
        if invoice is None:
            invoice = FaktorBuy.objects.create(user=user)
        else:
            invoice = _lock_draft(invoice, FaktorBuy)

        invoice.supplier = (supplier or "").strip()[:200]
        invoice.description = (description or "").strip()
        invoice.save(update_fields=["supplier", "description", "updated_at"])

        invoice.items.all().delete()
        total = Decimal("0")
        for line in lines:
            product = line["product"]
            qty = line["quantity"]
            unit_price = line.get("unit_price")
            if unit_price is None:
                unit_price = product.price_for_company
            item = FaktorItem(
                buy=invoice,
                product=product,
                product_name=product.name,
                barcode=product.serial_number,
                quantity=qty,
                unit_price=unit_price,
                cost_price=unit_price,
            )
            item.save()
            total += item.total_price

        invoice.total_price = total.quantize(Decimal("0.01"))
        invoice.save(update_fields=["total_price", "updated_at"])
    return invoice


# ---------------------------------------------------------------------------
# نهایی‌سازی
# ---------------------------------------------------------------------------
def _sync_sell(invoice) -> str | None:
    try:
        post_sell(invoice)
        return None
    except AccountantUnavailable as exc:
        return str(exc)


def _sync_buy(invoice) -> str | None:
    try:
        post_buy(invoice)
        return None
    except AccountantUnavailable as exc:
        return str(exc)


def finalize_sell(invoice) -> tuple[FaktorSell, bool, str | None]:
    """
    موجودی را کم، قیمت‌ها را از سرور بازمحاسبه و فاکتور را نهایی می‌کند.
    خروجی: (فاکتور، تازه‌نهایی‌شده؟، خطای حسابدار)
    """
    with transaction.atomic():
        invoice = FaktorSell.objects.select_for_update().get(pk=invoice.pk)
        if invoice.status == InvoiceStatus.COMPLETED:
            return invoice, False, None

        items = list(invoice.items.select_related("product"))
        if not items:
            raise InvoiceError("فاکتور خالی را نمی‌توان نهایی کرد.")

        total = Decimal("0")
        for item in items:
            if not item.product_id:
                raise InvoiceError(f"کالای «{item.product_name}» از سیستم حذف شده است.")
            try:
                product = Product.objects.select_for_update().get(pk=item.product_id)
            except Product.DoesNotExist:
                raise InvoiceError(f"کالای «{item.product_name}» پیدا نشد.")

            qty = item.quantity
            if product.count < qty:
                raise StockError(
                    f"موجودی «{product.name}» کافی نیست (موجودی: {product.count}، درخواست: {qty})."
                )

            updated = Product.objects.filter(pk=product.pk, count__gte=qty).update(
                count=F("count") - qty
            )
            if not updated:
                raise StockError(
                    f"موجودی «{product.name}» همین لحظه تمام شد؛ دوباره تلاش کنید."
                )

            item.unit_price = product.final_price_for_customer()
            item.cost_price = product.price_for_company
            item.product_name = product.name
            item.barcode = product.serial_number
            item.save(update_fields=["unit_price", "cost_price", "product_name", "barcode"])
            total += item.total_price

        invoice.total_price = total.quantize(Decimal("0.01"))
        invoice.status = InvoiceStatus.COMPLETED
        invoice.completed_at = timezone.now()
        invoice.save(update_fields=["total_price", "status", "completed_at", "updated_at"])

    sync_error = _sync_sell(invoice)
    invoice.refresh_from_db(fields=["accounted", "accounted_at"])
    return invoice, True, sync_error


def finalize_buy(invoice) -> tuple[FaktorBuy, bool, str | None]:
    """موجودی را زیاد و قیمت خرید کالا را با آخرین قیمت خرید به‌روز می‌کند."""
    with transaction.atomic():
        invoice = FaktorBuy.objects.select_for_update().get(pk=invoice.pk)
        if invoice.status == InvoiceStatus.COMPLETED:
            return invoice, False, None

        items = list(invoice.items.select_related("product"))
        if not items:
            raise InvoiceError("فاکتور خالی را نمی‌توان نهایی کرد.")

        total = Decimal("0")
        for item in items:
            if not item.product_id:
                raise InvoiceError(f"کالای «{item.product_name}» از سیستم حذف شده است.")
            try:
                product = Product.objects.select_for_update().get(pk=item.product_id)
            except Product.DoesNotExist:
                raise InvoiceError(f"کالای «{item.product_name}» پیدا نشد.")

            item.unit_price = clean_price(item.unit_price)
            item.cost_price = item.unit_price
            item.product_name = product.name
            item.barcode = product.serial_number
            item.save(update_fields=["unit_price", "cost_price", "product_name", "barcode"])

            Product.objects.filter(pk=product.pk).update(
                count=F("count") + item.quantity,
                price_for_company=item.unit_price,
            )
            total += item.total_price

        invoice.total_price = total.quantize(Decimal("0.01"))
        invoice.status = InvoiceStatus.COMPLETED
        invoice.completed_at = timezone.now()
        invoice.save(update_fields=["total_price", "status", "completed_at", "updated_at"])

    sync_error = _sync_buy(invoice)
    invoice.refresh_from_db(fields=["accounted", "accounted_at"])
    return invoice, True, sync_error


# ---------------------------------------------------------------------------
# خرید از روی OCR
# ---------------------------------------------------------------------------
def create_buy_from_rows(*, rows, user, supplier="", description=""):
    """
    rows: [{'name','barcode','quantity','unit_price'}]
    کالاهای ناشناس ساخته می‌شوند، موجودی زیاد می‌شود و فاکتور نهایی + حسابدار ثبت می‌شود.
    """
    if not rows:
        raise InvoiceError("هیچ ردیفی برای ثبت وجود ندارد.")
    shop = ShopSettings.load()
    markup = shop.default_markup_percent or Decimal("0")
    created_products = 0

    with transaction.atomic():
        buy = FaktorBuy.objects.create(user=user, supplier=(supplier or "").strip()[:200], description=description or "")
        for row in rows:
            name = (row.get("name") or "").strip()
            barcode = (row.get("barcode") or "").strip()
            qty = clean_quantity(row.get("quantity"))
            unit_price = clean_price(row.get("unit_price"))
            if not name and not barcode:
                raise InvoiceError("هر ردیف باید نام یا بارکد داشته باشد.")

            product = None
            if barcode:
                product = Product.objects.filter(serial_number=barcode).first()
            if product is None and name:
                product = Product.objects.filter(name__iexact=name).first()
            if product is None and name:
                product = Product.objects.filter(name__icontains=name).first()
            if product is None:
                if not name:
                    name = f"کالای {barcode}"
                product = Product.objects.create(
                    name=name[:200],
                    serial_number=barcode,
                    price_for_company=unit_price,
                    price_for_customer=(unit_price * (Decimal("1") + markup / Decimal("100"))).quantize(
                        Decimal("0.01")
                    ),
                    count=0,
                )
                created_products += 1

            FaktorItem.objects.create(
                buy=buy,
                product=product,
                product_name=product.name,
                barcode=product.serial_number,
                quantity=qty,
                unit_price=unit_price,
                cost_price=unit_price,
            )

        total = sum((item.total_price for item in buy.items.all()), Decimal("0"))
        buy.total_price = total.quantize(Decimal("0.01"))
        buy.save(update_fields=["total_price"])

    buy, _, sync_error = finalize_buy(buy)
    return buy, created_products, sync_error


# ---------------------------------------------------------------------------
# حذف / ابطال
# ---------------------------------------------------------------------------
def delete_draft_sell(invoice):
    if invoice.status != InvoiceStatus.DRAFT:
        raise InvoiceError("فقط پیش‌نویس قابل حذف است.")
    invoice.delete()


def delete_or_void_sell(invoice):
    """پیش‌نویس را حذف؛ فاکتور نهایی را ابطال و موجودی را برمی‌گرداند."""
    if invoice.status == InvoiceStatus.DRAFT:
        invoice.delete()
        return "deleted"

    with transaction.atomic():
        invoice = FaktorSell.objects.select_for_update().get(pk=invoice.pk)
        for item in invoice.items.all():
            if item.product_id:
                Product.objects.filter(pk=item.product_id).update(count=F("count") + item.quantity)
        try:
            void_accountant(AccountantInvoice.KIND_SELL, invoice.pk)
        except AccountantUnavailable as exc:
            raise InvoiceError(
                "دیتابیس حسابدار در دسترس نیست؛ ابطال انجام نشد تا سابقه ناهماهنگ نشود."
            ) from exc
        invoice.delete()
    return "voided"


def delete_buy(invoice):
    if invoice.status != InvoiceStatus.DRAFT:
        raise InvoiceError("فاکتور خرید نهایی‌شده قابل حذف نیست؛ برای اصلاح، فاکتور معکوس ثبت کنید.")
    invoice.delete()
