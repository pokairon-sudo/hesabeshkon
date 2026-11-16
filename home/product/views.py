import csv

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView

from accounts.mixins import AdminRequiredMixin, AppAccessRequiredMixin
from core.models import ShopSettings

from .forms import ProductForm
from .models import Product, generate_barcode
from .utils import product_payload


def _wants_json(request) -> bool:
    return (
        request.POST.get("respond_json") == "1"
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in request.headers.get("Accept", "")
    )


def _form_errors(form):
    return {field: [str(e) for e in errors] for field, errors in form.errors.items()}


class ProductListView(AppAccessRequiredMixin, ListView):
    model = Product
    template_name = "product/list.html"
    context_object_name = "products"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        field = self.request.GET.get("field", "")
        tag = self.request.GET.get("tag", "").strip()
        low = self.request.GET.get("low") == "1"

        if q:
            if field == "barcode":
                qs = qs.filter(serial_number__icontains=q)
            elif field == "tag":
                qs = qs.filter(tag__icontains=q)
            else:
                qs = qs.filter(
                    Q(name__icontains=q)
                    | Q(serial_number__icontains=q)
                    | Q(tag__icontains=q)
                )
        if tag:
            qs = qs.filter(tag=tag)
        if low:
            qs = qs.filter(count__lte=ShopSettings.load().low_stock_threshold)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        context["field"] = self.request.GET.get("field", "")
        context["low"] = self.request.GET.get("low") == "1"
        context["threshold"] = ShopSettings.load().low_stock_threshold
        context["tags"] = (
            Product.objects.exclude(tag="").values_list("tag", flat=True).distinct().order_by("tag")
        )
        return context


class CreateProductView(AppAccessRequiredMixin, View):
    template_name = "product/form.html"

    def get(self, request):
        form = ProductForm()
        return render(
            request,
            self.template_name,
            {"form": form, "is_new": True},
        )

    def post(self, request):
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            if _wants_json(request):
                return JsonResponse({"success": True, "product": product_payload(product)})
            messages.success(request, f"کالای «{product.name}» ثبت شد.")
            return redirect("product:l-product")

        if _wants_json(request):
            return JsonResponse({"success": False, "errors": _form_errors(form)}, status=400)
        return render(
            request,
            self.template_name,
            {"form": form, "is_new": True},
            status=400,
        )


class EditProductView(AppAccessRequiredMixin, View):
    template_name = "product/form.html"

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        return render(
            request,
            self.template_name,
            {"form": ProductForm(instance=product), "product": product, "is_new": False},
        )

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            product = form.save()
            if _wants_json(request):
                return JsonResponse({"success": True, "product": product_payload(product)})
            messages.success(request, f"کالای «{product.name}» ویرایش شد.")
            return redirect("product:l-product")

        if _wants_json(request):
            return JsonResponse({"success": False, "errors": _form_errors(form)}, status=400)
        return render(
            request,
            self.template_name,
            {"form": form, "product": product, "is_new": False},
            status=400,
        )


class DeleteProductView(AdminRequiredMixin, View):
    def post(self, request, pk):
        from faktor.models import FaktorItem, InvoiceStatus

        product = get_object_or_404(Product, pk=pk)
        in_draft = FaktorItem.objects.filter(
            product=product,
            sell__status=InvoiceStatus.DRAFT,
        ).exists() or FaktorItem.objects.filter(
            product=product,
            buy__status=InvoiceStatus.DRAFT,
        ).exists()
        if in_draft:
            messages.error(
                request,
                f"کالای «{product.name}» در یک فاکتور پیش‌نویس استفاده شده است؛ اول آن پیش‌نویس را حذف/اصلاح کنید.",
            )
            return redirect("product:e-product", pk=product.pk)
        name = product.name
        product.delete()
        messages.success(request, f"کالای «{name}» حذف شد.")
        return redirect("product:l-product")


class BarcodeLookupView(AppAccessRequiredMixin, View):
    def get(self, request, barcode):
        product = Product.objects.filter(serial_number=barcode.strip()).first()
        if not product:
            return JsonResponse({"success": False, "error": "کالایی با این بارکد پیدا نشد."}, status=404)
        return JsonResponse(
            {
                "success": True,
                "product": product_payload(product, include_cost=request.user.is_admin),
            }
        )


class ProductDetailView(AppAccessRequiredMixin, View):
    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        return JsonResponse({"success": True, "product": product_payload(product)})


class NewBarcodeView(AppAccessRequiredMixin, View):
    def get(self, request):
        return JsonResponse({"barcode": generate_barcode()})


class ExportProductsView(AdminRequiredMixin, View):
    def get(self, request):
        response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
        response["Content-Disposition"] = 'attachment; filename="products.csv"'
        writer = csv.writer(response)
        writer.writerow(
            ["name", "barcode", "tag", "unit", "buy_price", "sell_price", "final_price", "count"]
        )
        for p in Product.objects.all():
            writer.writerow(
                [
                    p.name,
                    p.serial_number,
                    p.tag,
                    p.get_unit_display(),
                    p.price_for_company,
                    p.price_for_customer,
                    p.final_price_for_customer(),
                    p.count,
                ]
            )
        return response
