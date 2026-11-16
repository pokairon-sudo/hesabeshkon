import csv
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import ListView

from accounts.mixins import AdminRequiredMixin, AppAccessRequiredMixin
from core.models import ShopSettings
from product.models import Product
from product.utils import product_payload

from .models import FaktorBuy, FaktorItem, FaktorSell, InvoiceStatus
from .ocr import OCRInputError, extract_receipt, extract_receipt_from_text, parse_invoice_text
from .receipt import receipt_summary, receipt_to_rows
from .services import (
    InvoiceError,
    StockError,
    clean_price,
    clean_quantity,
    create_buy_from_rows,
    delete_buy,
    delete_or_void_sell,
    finalize_buy,
    finalize_sell,
    save_buy_from_cart,
    save_sell_from_cart,
)

logger = logging.getLogger("faktor")


# ---------------------------------------------------------------------------
# کمک‌کننده‌ها
# ---------------------------------------------------------------------------
def wants_json(request) -> bool:
    return (
        request.POST.get("respond_json") == "1"
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in request.headers.get("Accept", "")
    )


def invoice_for_user(model, pk, user):
    qs = model.objects.all()
    if not user.is_admin:
        qs = qs.filter(user=user)
    return get_object_or_404(qs, pk=pk)


def parse_cart(request, mode: str):
    """سبد JSON را اعتبارسنجی می‌کند؛ قیمت فروش همیشه از سرور می‌آید."""
    raw = request.POST.get("cart_json") or "[]"
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        raise InvoiceError("سبد خرید نامعتبر است.")
    if not isinstance(data, list):
        raise InvoiceError("سبد خرید نامعتبر است.")
    if not data:
        raise InvoiceError("حداقل یک کالا به فاکتور اضافه کنید.")
    if len(data) > settings.MAX_INVOICE_LINES:
        raise InvoiceError("تعداد ردیف‌های فاکتور بیش از حد مجاز است.")

    merged: dict[int, dict] = {}
    for row in data:
        if not isinstance(row, dict):
            raise InvoiceError("یکی از ردیف‌ها نامعتبر است.")
        try:
            product_id = int(row.get("product_id"))
        except (TypeError, ValueError):
            raise InvoiceError("شناسه کالا نامعتبر است.")
        qty = clean_quantity(row.get("quantity", 1))
        if qty > settings.MAX_LINE_QUANTITY:
            raise InvoiceError("تعداد در یک ردیف بیش از حد مجاز است.")
        entry = merged.setdefault(product_id, {"quantity": 0, "unit_price": None})
        entry["quantity"] += qty
        if mode == "buy" and row.get("unit_price") not in (None, ""):
            entry["unit_price"] = row.get("unit_price")

    products = Product.objects.in_bulk(list(merged.keys()))
    lines = []
    for product_id, entry in merged.items():
        product = products.get(product_id)
        if not product:
            raise InvoiceError("یکی از کالاها دیگر در سیستم موجود نیست.")
        if not product.is_active:
            raise InvoiceError(f"کالای «{product.name}» غیرفعال است.")
        line = {"product": product, "quantity": entry["quantity"]}
        if mode == "buy":
            raw_price = entry["unit_price"]
            line["unit_price"] = (
                clean_price(raw_price) if raw_price not in (None, "") else product.price_for_company
            )
        lines.append(line)
    return lines


def invoice_payload(invoice, kind: str) -> dict:
    preview = (
        reverse("faktor:sell-preview", kwargs={"pk": invoice.pk})
        if kind == "sell"
        else reverse("faktor:buy-preview", kwargs={"pk": invoice.pk})
    )
    return {
        "id": invoice.pk,
        "kind": kind,
        "number": invoice.number,
        "status": invoice.status,
        "status_label": invoice.get_status_display(),
        "total": str(invoice.total_price),
        "preview_url": preview,
        "print_url": f"{preview}?format=receipt&autoprint=1",
        "edit_url": (
            reverse("faktor:sell-edit", kwargs={"pk": invoice.pk})
            if kind == "sell"
            else reverse("faktor:buy-edit", kwargs={"pk": invoice.pk})
        ),
    }


def seed_items(invoice, mode: str) -> list[dict]:
    if not invoice:
        return []
    rows = []
    for item in invoice.items.all():
        rows.append(
            {
                "product_id": item.product_id,
                "name": item.product_name or (item.product.name if item.product else "کالا"),
                "serial_number": item.barcode or "",
                "quantity": item.quantity,
                "unit_price": str(item.unit_price),
                "count": item.product.count if item.product else 0,
                "unit": item.product.get_unit_display() if item.product else "",
            }
        )
    return rows


def render_invoice(request, mode, invoice=None, *, status=200, cart_json="[]", customer="", supplier="", description=""):
    is_sell = mode == "sell"
    context = {
        "mode": mode,
        "invoice": invoice,
        "cart_seed": seed_items(invoice, mode),
        "cart_json": cart_json,
        "customer_value": customer or (invoice.customer if invoice and is_sell else ""),
        "supplier_value": supplier or (invoice.supplier if invoice and not is_sell else ""),
        "description_value": description or (invoice.description if invoice else ""),
        "submit_url": (
            reverse("faktor:sell-edit", kwargs={"pk": invoice.pk})
            if invoice and is_sell
            else reverse("faktor:sell-create")
            if is_sell
            else reverse("faktor:buy-edit", kwargs={"pk": invoice.pk})
            if invoice
            else reverse("faktor:buy-create")
        ),
        "search_url": reverse("faktor:search-products"),
        "product_create_url": reverse("product:c-product"),
        "new_barcode_url": reverse("product:new-barcode"),
        "today": timezone.localdate(),
    }
    return render(request, "faktor/invoice_form.html", context, status=status)


# ---------------------------------------------------------------------------
# فروش
# ---------------------------------------------------------------------------
class SellInvoiceView(AppAccessRequiredMixin, View):
    def get(self, request, pk=None):
        invoice = invoice_for_user(FaktorSell, pk, request.user) if pk else None
        if invoice and invoice.status != InvoiceStatus.DRAFT:
            messages.info(request, "فاکتور نهایی‌شده قابل ویرایش نیست؛ فقط پیش‌نمایش/چاپ.")
            return redirect("faktor:sell-preview", pk=invoice.pk)
        return render_invoice(request, "sell", invoice)

    def post(self, request, pk=None):
        invoice = invoice_for_user(FaktorSell, pk, request.user) if pk else None
        if invoice and invoice.status != InvoiceStatus.DRAFT:
            error = "فاکتور نهایی‌شده قابل ویرایش نیست."
            if wants_json(request):
                return JsonResponse({"success": False, "errors": [error]}, status=400)
            messages.error(request, error)
            return redirect("faktor:sell-preview", pk=invoice.pk)

        action = request.POST.get("action", "finalize")
        customer = request.POST.get("customer", "")
        description = request.POST.get("description", "")

        try:
            lines = parse_cart(request, "sell")
            invoice = save_sell_from_cart(
                invoice=invoice, lines=lines, customer=customer, description=description, user=request.user
            )
            if action == "draft":
                if wants_json(request):
                    payload = invoice_payload(invoice, "sell")
                    payload.update(
                        {
                            "success": True,
                            "message": f"پیش‌نویس {invoice.number} ذخیره شد؛ بعداً ادامه دهید.",
                        }
                    )
                    return JsonResponse(payload)
                messages.success(request, f"پیش‌نویس {invoice.number} ذخیره شد.")
                return redirect("faktor:sell-edit", pk=invoice.pk)

            invoice, changed, sync_error = finalize_sell(invoice)
        except (InvoiceError, StockError) as exc:
            if wants_json(request):
                payload = {"success": False, "errors": [str(exc)]}
                if invoice is not None and invoice.pk:
                    payload.update(invoice_payload(invoice, "sell"))
                    payload["draft_saved"] = invoice.status == InvoiceStatus.DRAFT
                return JsonResponse(payload, status=400)
            messages.error(request, str(exc))
            return render_invoice(
                request,
                "sell",
                invoice,
                status=400,
                cart_json=request.POST.get("cart_json", "[]"),
                customer=customer,
                description=description,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("sell invoice failed")
            if wants_json(request):
                return JsonResponse({"success": False, "errors": ["خطای غیرمنتظره در ثبت فاکتور."]}, status=500)
            messages.error(request, "خطای غیرمنتظره در ثبت فاکتور.")
            return render_invoice(request, "sell", invoice, status=500)

        if sync_error:
            messages.warning(request, f"فاکتور نهایی شد اما به حسابدار ارسال نشد: {sync_error}")
        if wants_json(request):
            payload = invoice_payload(invoice, "sell")
            payload.update({"success": True, "sync_error": sync_error, "changed": changed})
            return JsonResponse(payload)
        messages.success(request, f"فاکتور {invoice.number} نهایی شد.")
        return redirect("faktor:sell-preview", pk=invoice.pk)


class SellListView(AppAccessRequiredMixin, ListView):
    model = FaktorSell
    template_name = "faktor/invoice_list.html"
    context_object_name = "invoices"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related("user").annotate(line_count=Count("items")).order_by("-date", "-id")
        if not self.request.user.is_admin:
            qs = qs.filter(user=self.request.user)
        status = self.request.GET.get("status", "")
        if status in (InvoiceStatus.DRAFT, InvoiceStatus.COMPLETED):
            qs = qs.filter(status=status)
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(number__icontains=q) | Q(customer__icontains=q))
        start_raw = self.request.GET.get("from", "")
        end_raw = self.request.GET.get("to", "")
        today = timezone.localdate()
        start = _parse_date(start_raw, None)
        end = _parse_date(end_raw, None)
        if start:
            qs = qs.filter(date__gte=start)
        if end:
            qs = qs.filter(date__lte=end)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base = FaktorSell.objects.all()
        if not self.request.user.is_admin:
            base = base.filter(user=self.request.user)
        start = _parse_date(self.request.GET.get("from", ""), None)
        end = _parse_date(self.request.GET.get("to", ""), None)
        context.update(
            {
                "q": self.request.GET.get("q", ""),
                "status_filter": self.request.GET.get("status", ""),
                "from": start.strftime("%Y-%m-%d") if start else "",
                "to": end.strftime("%Y-%m-%d") if end else "",
                "draft_count": base.filter(status=InvoiceStatus.DRAFT).count(),
                "completed_count": base.filter(status=InvoiceStatus.COMPLETED).count(),
                "mode": "sell",
            }
        )
        return context


class SellDeleteView(AppAccessRequiredMixin, View):
    def post(self, request, pk):
        invoice = invoice_for_user(FaktorSell, pk, request.user)
        if invoice.is_completed and not request.user.is_admin:
            messages.error(request, "فقط مدیر می‌تواند فاکتور نهایی را ابطال کند.")
            return redirect("faktor:sell-preview", pk=invoice.pk)
        try:
            result = delete_or_void_sell(invoice)
        except InvoiceError as exc:
            messages.error(request, str(exc))
            return redirect("faktor:sell-preview", pk=invoice.pk)
        if result == "deleted":
            messages.success(request, f"پیش‌نویس {invoice.number} حذف شد.")
        else:
            messages.success(request, f"فاکتور {invoice.number} ابطال شد و موجودی برگشت.")
        return redirect("faktor:sell-list")


class SellPreviewView(AppAccessRequiredMixin, View):
    template_name = "faktor/invoice_preview.html"

    def get(self, request, pk):
        invoice = invoice_for_user(FaktorSell, pk, request.user)
        return render(
            request,
            self.template_name,
            {
                "kind": "sell",
                "invoice": invoice,
                "items": invoice.items.select_related("product"),
                "party": invoice.customer,
                "party_label": "مشتری",
                "back_url": reverse("faktor:sell-list"),
                "edit_url": reverse("faktor:sell-edit", kwargs={"pk": invoice.pk}) if invoice.is_draft else "",
                "print_format": request.GET.get("format", "receipt"),
                "autoprint": request.GET.get("autoprint") == "1",
                "today": timezone.localdate(),
            },
        )


# ---------------------------------------------------------------------------
# خرید
# ---------------------------------------------------------------------------
class BuyEnabledMixin:
    def dispatch(self, request, *args, **kwargs):
        if not getattr(settings, "FAKTOR_BUY_ENABLED", True):
            messages.error(request, "فاکتور خرید موقتاً غیرفعال است.")
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)


class BuyInvoiceView(BuyEnabledMixin, AppAccessRequiredMixin, View):
    def get(self, request, pk=None):
        invoice = invoice_for_user(FaktorBuy, pk, request.user) if pk else None
        if invoice and invoice.status != InvoiceStatus.DRAFT:
            messages.info(request, "فاکتور خرید نهایی‌شده قابل ویرایش نیست.")
            return redirect("faktor:buy-preview", pk=invoice.pk)
        return render_invoice(request, "buy", invoice)

    def post(self, request, pk=None):
        invoice = invoice_for_user(FaktorBuy, pk, request.user) if pk else None
        if invoice and invoice.status != InvoiceStatus.DRAFT:
            error = "فاکتور خرید نهایی‌شده قابل ویرایش نیست."
            if wants_json(request):
                return JsonResponse({"success": False, "errors": [error]}, status=400)
            messages.error(request, error)
            return redirect("faktor:buy-preview", pk=invoice.pk)

        action = request.POST.get("action", "finalize")
        supplier = request.POST.get("supplier", "")
        description = request.POST.get("description", "")
        try:
            lines = parse_cart(request, "buy")
            invoice = save_buy_from_cart(
                invoice=invoice, lines=lines, supplier=supplier, description=description, user=request.user
            )
            if action == "draft":
                if wants_json(request):
                    payload = invoice_payload(invoice, "buy")
                    payload.update(
                        {"success": True, "message": f"پیش‌نویس خرید {invoice.number} ذخیره شد."}
                    )
                    return JsonResponse(payload)
                messages.success(request, f"پیش‌نویس خرید {invoice.number} ذخیره شد.")
                return redirect("faktor:buy-edit", pk=invoice.pk)

            invoice, changed, sync_error = finalize_buy(invoice)
        except (InvoiceError, StockError) as exc:
            if wants_json(request):
                payload = {"success": False, "errors": [str(exc)]}
                if invoice is not None and invoice.pk:
                    payload.update(invoice_payload(invoice, "buy"))
                    payload["draft_saved"] = invoice.status == InvoiceStatus.DRAFT
                return JsonResponse(payload, status=400)
            messages.error(request, str(exc))
            return render_invoice(
                request,
                "buy",
                invoice,
                status=400,
                cart_json=request.POST.get("cart_json", "[]"),
                supplier=supplier,
                description=description,
            )
        except Exception:  # noqa: BLE001
            logger.exception("buy invoice failed")
            if wants_json(request):
                return JsonResponse({"success": False, "errors": ["خطای غیرمنتظره در ثبت فاکتور."]}, status=500)
            messages.error(request, "خطای غیرمنتظره در ثبت فاکتور.")
            return render_invoice(request, "buy", invoice, status=500)

        if sync_error:
            messages.warning(request, f"فاکتور نهایی شد اما به حسابدار ارسال نشد: {sync_error}")
        if wants_json(request):
            payload = invoice_payload(invoice, "buy")
            payload.update({"success": True, "sync_error": sync_error, "changed": changed})
            return JsonResponse(payload)
        messages.success(request, f"فاکتور خرید {invoice.number} نهایی شد.")
        return redirect("faktor:buy-preview", pk=invoice.pk)


class BuyListView(BuyEnabledMixin, AppAccessRequiredMixin, ListView):
    model = FaktorBuy
    template_name = "faktor/invoice_list.html"
    context_object_name = "invoices"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related("user").annotate(line_count=Count("items")).order_by("-date", "-id")
        if not self.request.user.is_admin:
            qs = qs.filter(user=self.request.user)
        status = self.request.GET.get("status", "")
        if status in (InvoiceStatus.DRAFT, InvoiceStatus.COMPLETED):
            qs = qs.filter(status=status)
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(number__icontains=q) | Q(supplier__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base = FaktorBuy.objects.all()
        if not self.request.user.is_admin:
            base = base.filter(user=self.request.user)
        context.update(
            {
                "q": self.request.GET.get("q", ""),
                "status_filter": self.request.GET.get("status", ""),
                "draft_count": base.filter(status=InvoiceStatus.DRAFT).count(),
                "completed_count": base.filter(status=InvoiceStatus.COMPLETED).count(),
                "mode": "buy",
            }
        )
        return context


class BuyPreviewView(BuyEnabledMixin, AppAccessRequiredMixin, View):
    template_name = "faktor/invoice_preview.html"

    def get(self, request, pk):
        invoice = invoice_for_user(FaktorBuy, pk, request.user)
        return render(
            request,
            self.template_name,
            {
                "kind": "buy",
                "invoice": invoice,
                "items": invoice.items.select_related("product"),
                "party": invoice.supplier,
                "party_label": "تأمین‌کننده",
                "back_url": reverse("faktor:buy-list"),
                "edit_url": reverse("faktor:buy-edit", kwargs={"pk": invoice.pk}) if invoice.is_draft else "",
                "print_format": request.GET.get("format", "receipt"),
                "autoprint": request.GET.get("autoprint") == "1",
                "today": timezone.localdate(),
            },
        )


class BuyDeleteView(BuyEnabledMixin, AppAccessRequiredMixin, View):
    def post(self, request, pk):
        invoice = invoice_for_user(FaktorBuy, pk, request.user)
        try:
            delete_buy(invoice)
        except InvoiceError as exc:
            messages.error(request, str(exc))
            return redirect("faktor:buy-preview", pk=invoice.pk)
        messages.success(request, f"پیش‌نویس خرید {invoice.number} حذف شد.")
        return redirect("faktor:buy-list")


# ---------------------------------------------------------------------------
# جستجو و API
# ---------------------------------------------------------------------------
class SearchProductsView(AppAccessRequiredMixin, View):
    def get(self, request):
        q = request.GET.get("q", "").strip()
        if not q:
            return JsonResponse({"results": []})
        products = (
            Product.objects.filter(is_active=True)
            .filter(Q(serial_number__iexact=q) | Q(name__icontains=q) | Q(tag__icontains=q) | Q(serial_number__icontains=q))
            .order_by("-serial_number")
            .distinct()[:20]
        )
        # کارکنان (مدیر و اپراتور) برای ثبت فاکتور خرید به قیمت خرید نیاز دارند.
        results = [product_payload(p, include_cost=True) for p in products]
        exact = next((r for r in results if r["serial_number"].lower() == q.lower()), None)
        if exact:
            results.remove(exact)
            results.insert(0, exact)
        return JsonResponse({"results": results, "exact": bool(exact)})


class AddItemView(AppAccessRequiredMixin, View):
    """افزودن یک قلم به پیش‌نویس (برای اپراتور/مدیر). موجودی دست نمی‌خورد."""

    def post(self, request):
        faktor_id = request.POST.get("faktor_id")
        product_id = request.POST.get("product_id")
        barcode = request.POST.get("barcode")
        qty = request.POST.get("quantity", 1)
        try:
            qty = clean_quantity(qty)
            if product_id:
                product = Product.objects.get(pk=product_id)
            else:
                product = Product.objects.get(serial_number=barcode)
        except Product.DoesNotExist:
            return JsonResponse({"success": False, "error": "کالا پیدا نشد."}, status=404)
        except InvoiceError as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=400)

        if not faktor_id:
            return JsonResponse({"success": False, "error": "شناسه فاکتور لازم است."}, status=400)
        try:
            invoice = invoice_for_user(FaktorSell, faktor_id, request.user)
        except Exception:
            return JsonResponse({"success": False, "error": "فاکتور پیدا نشد."}, status=404)
        if invoice.status != InvoiceStatus.DRAFT:
            return JsonResponse({"success": False, "error": "فاکتور نهایی است."}, status=400)

        item = invoice.items.filter(product=product).first()
        if item:
            item.quantity += qty
            item.save(update_fields=["quantity"])
        else:
            item = FaktorItem.objects.create(
                sell=invoice,
                product=product,
                quantity=qty,
                unit_price=product.final_price_for_customer(),
                cost_price=product.price_for_company,
            )
        invoice.recalc_total()
        return JsonResponse(
            {
                "success": True,
                "item_id": item.pk,
                "quantity": item.quantity,
                "total": str(invoice.total_price),
            }
        )


# ---------------------------------------------------------------------------
# OCR فاکتور خرید
# ---------------------------------------------------------------------------
class OCRUploadView(BuyEnabledMixin, AppAccessRequiredMixin, View):
    template_name = "faktor/ocr_upload.html"

    def get(self, request):
        return render(request, self.template_name, {"raw_text": "", "rows": []})

    def post(self, request):
        raw_text = request.POST.get("text", "")
        warnings: list[str] = []
        receipt = None
        try:
            if request.FILES.get("image"):
                receipt = extract_receipt(request.FILES["image"])
                raw_text = receipt.raw_text
            elif raw_text.strip():
                receipt = extract_receipt_from_text(raw_text)
            else:
                raise OCRInputError("یک تصویر انتخاب کنید یا متن فاکتور را جای‌گذاری کنید.")
        except OCRInputError as exc:
            messages.error(request, str(exc))
            return render(request, self.template_name, {"raw_text": raw_text}, status=400)

        if receipt is not None:
            rows = receipt_to_rows(receipt)
            if not rows:
                # پشتیبان: پارسر قدیمی ساده‌تر است و ممکن است ردیف‌هایی پیدا کند.
                rows = parse_invoice_text(raw_text)
            warnings.extend(receipt.warnings)
        else:
            rows = parse_invoice_text(raw_text)

        for warning in warnings:
            messages.warning(request, warning)
        if not rows:
            messages.warning(
                request, "ردیفی از متن تشخیص داده نشد؛ می‌توانید متن را دستی‌تر یا ردیف‌ها را اصلاح کنید."
            )
        return render(
            request,
            "faktor/ocr_preview.html",
            {
                "raw_text": raw_text,
                "rows": rows,
                "rows_json": json.dumps(rows, ensure_ascii=False),
                "receipt": receipt_summary(receipt) if receipt else None,
                "today": timezone.localdate(),
            },
        )


class OCRConfirmView(BuyEnabledMixin, AppAccessRequiredMixin, View):
    def post(self, request):
        try:
            rows = json.loads(request.POST.get("rows_json", "[]"))
        except (TypeError, ValueError):
            messages.error(request, "داده‌های ردیف‌ها نامعتبر است.")
            return redirect("faktor:ocr")
        if not isinstance(rows, list) or not rows:
            messages.error(request, "هیچ ردیفی برای ثبت وجود ندارد.")
            return redirect("faktor:ocr")
        if len(rows) > 200:
            messages.error(request, "تعداد ردیف‌ها بیش از حد مجاز است.")
            return redirect("faktor:ocr")

        try:
            invoice, created_products, sync_error = create_buy_from_rows(
                rows=rows,
                user=request.user,
                supplier=request.POST.get("supplier", ""),
                description=request.POST.get("description", ""),
            )
        except InvoiceError as exc:
            messages.error(request, str(exc))
            return redirect("faktor:ocr")
        except Exception:  # noqa: BLE001
            logger.exception("OCR confirm failed")
            messages.error(request, "ثبت فاکتور OCR با خطا مواجه شد.")
            return redirect("faktor:ocr")

        messages.success(
            request,
            f"فاکتور خرید {invoice.number} با {invoice.items.count()} ردیف ثبت شد"
            + (f" و {created_products} کالای جدید ساخته شد." if created_products else "."),
        )
        if sync_error:
            messages.warning(request, f"ارسال به حسابدار انجام نشد: {sync_error}")
        return redirect("faktor:buy-preview", pk=invoice.pk)


# ---------------------------------------------------------------------------
# گزارش‌ها
# ---------------------------------------------------------------------------
def _parse_date(value, default):
    if not value:
        return default
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return default


class ReportsView(AdminRequiredMixin, View):
    template_name = "faktor/reports.html"

    def get_context(self, request):
        today = timezone.localdate()
        start = _parse_date(request.GET.get("from"), today - timedelta(days=29))
        end = _parse_date(request.GET.get("to"), today)
        if start > end:
            start, end = end, start

        sells = FaktorSell.objects.filter(
            status=InvoiceStatus.COMPLETED, date__gte=start, date__lte=end
        )
        items = list(
            FaktorItem.objects.filter(sell__in=sells).select_related("product", "sell")
        )
        revenue = sum((item.total_price for item in items), Decimal("0"))
        cost = sum((item.cost_price * item.quantity for item in items), Decimal("0"))
        profit = revenue - cost
        items_sold = sum(item.quantity for item in items)

        buys = FaktorBuy.objects.filter(
            status=InvoiceStatus.COMPLETED, date__gte=start, date__lte=end
        )
        buy_total = sum((buy.total_price for buy in buys), Decimal("0"))

        # نمودار روزانه (حداکثر ۶۰ نقطه)
        series = {}
        cursor = start
        while cursor <= end and len(series) < 62:
            series[cursor] = {"revenue": Decimal("0"), "profit": Decimal("0")}
            cursor += timedelta(days=1)
        for item in items:
            day = item.sell.date
            if day in series:
                series[day]["revenue"] += item.total_price
                series[day]["profit"] += item.profit
        max_daily = max((v["revenue"] for v in series.values()), default=Decimal("0")) or Decimal("1")
        daily = [
            {
                "date": day,
                "revenue": value["revenue"],
                "profit": value["profit"],
                "height": max(2, int((value["revenue"] / max_daily) * 100)),
                "profit_height": max(
                    2,
                    int((value["profit"] / max_daily) * 100) if value["profit"] > 0 else 0,
                ),
            }
            for day, value in series.items()
        ]

        by_product = {}
        for item in items:
            key = item.product_name or "کالای حذف‌شده"
            row = by_product.setdefault(
                key, {"qty": 0, "revenue": Decimal("0"), "profit": Decimal("0")}
            )
            row["qty"] += item.quantity
            row["revenue"] += item.total_price
            row["profit"] += item.profit
        top_products = sorted(by_product.items(), key=lambda x: x[1]["profit"], reverse=True)[:12]

        low_stock = [
            p
            for p in Product.objects.filter(is_active=True).order_by("count")
            if p.count <= ShopSettings.load().low_stock_threshold
        ][:20]
        inventory = list(Product.objects.filter(is_active=True))
        inventory_cost = sum((p.price_for_company * p.count for p in inventory), Decimal("0"))
        inventory_retail = sum((p.final_price_for_customer() * p.count for p in inventory), Decimal("0"))

        context = {
            "start": start,
            "end": end,
            "revenue": revenue,
            "cost": cost,
            "profit": profit,
            "margin": (profit / revenue * 100) if revenue else Decimal("0"),
            "buy_total": buy_total,
            "buy_count": buys.count(),
            "sell_count": sells.count(),
            "items_sold": items_sold,
            "daily": daily,
            "top_products": top_products,
            "low_stock": low_stock,
            "threshold": ShopSettings.load().low_stock_threshold,
            "inventory_cost": inventory_cost,
            "inventory_retail": inventory_retail,
            "unaccounted": FaktorSell.objects.filter(
                status=InvoiceStatus.COMPLETED, accounted=False
            ).count()
            + FaktorBuy.objects.filter(status=InvoiceStatus.COMPLETED, accounted=False).count(),
            "recent": FaktorSell.objects.filter(status=InvoiceStatus.COMPLETED)
            .select_related("user")
            .order_by("-date", "-id")[:10],
            "query_string": request.GET.urlencode(),
        }
        return context

    def get(self, request):
        return render(request, self.template_name, self.get_context(request))


class ReportsExportView(AdminRequiredMixin, View):
    def get(self, request):
        today = timezone.localdate()
        start = _parse_date(request.GET.get("from"), today - timedelta(days=29))
        end = _parse_date(request.GET.get("to"), today)
        if start > end:
            start, end = end, start
        response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
        response["Content-Disposition"] = f'attachment; filename="sales-{start}-{end}.csv"'
        writer = csv.writer(response)
        writer.writerow(
            ["number", "date", "customer", "product", "barcode", "qty", "unit_price", "line_total", "cost_price", "profit"]
        )
        items = FaktorItem.objects.filter(
            sell__status=InvoiceStatus.COMPLETED, sell__date__gte=start, sell__date__lte=end
        ).select_related("sell")
        for item in items:
            writer.writerow(
                [
                    item.sell.number,
                    item.sell.date,
                    item.sell.customer,
                    item.product_name,
                    item.barcode,
                    item.quantity,
                    item.unit_price,
                    item.total_price,
                    item.cost_price,
                    item.profit,
                ]
            )
        return response
