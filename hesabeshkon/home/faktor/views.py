# faktor/views.py
import json
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import models as db_models, transaction
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DeleteView,
)
from django.http import JsonResponse
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from accounts.mixins import StaffGroupRequiredMixin
from django.contrib import messages
from django.db.models import Sum, F, DecimalField
from django.db.models.functions import Coalesce
from datetime import timedelta

from .models import FaktorSell, FaktorBuy, FaktorItem
from .forms import FaktorSellForm, FaktorBuyForm
from product.models import Product


class BuyEnabledRequiredMixin:
    """
    Buy invoices are temporarily disabled. Every buy view checks this
    first so a disabled feature fails with a clear message instead of a
    confusing 403. Flip settings.FAKTOR_BUY_ENABLED back to True to
    restore access — nothing else needs to change.
    """

    def dispatch(self, request, *args, **kwargs):
        if not getattr(settings, "FAKTOR_BUY_ENABLED", True):
            messages.error(request, "Buy invoices are temporarily disabled.")
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)


# ----------------------------------------------------------------------
# SEARCH (shared by sell + buy)
# ----------------------------------------------------------------------
class SearchProductsView(StaffGroupRequiredMixin, View):
    """
    Live product search by barcode (serial_number), name, or tag.
    Returns JSON; the invoice-form JS renders a dropdown.
    """

    def get(self, request):
        query = request.GET.get("q", "").strip()
        if len(query) < 1:
            return JsonResponse({"results": []})

        products = Product.objects.filter(
            db_models.Q(serial_number__icontains=query)
            | db_models.Q(name__icontains=query)
            | db_models.Q(tag__icontains=query)
        )[:15]

        results = [
            {
                "id": p.pk,
                "name": p.name,
                "tag": p.tag,
                "serial_number": p.serial_number,
                "count": p.count,
                "price_for_customer": str(p.final_price_for_customer()),
                "price_for_company": str(p.price_for_company),
            }
            for p in products
        ]
        return JsonResponse({"results": results})


# ----------------------------------------------------------------------
# SELL VIEWS
# ----------------------------------------------------------------------
class CreateFaktorSellView(StaffGroupRequiredMixin, View):
    """
    Nothing touches the database on GET. Scanned items live in a
    client-side cart (JS). The entire invoice is submitted in ONE POST
    when F7/F8/F9 is pressed and created atomically:
      - empty cart is rejected (never saves an empty invoice)
      - invoice number assigned by the model at save time
      - success always redirects back to this same page, fresh and empty
    """
    template_name = "faktor/faktor_sell_create.html"

    def get(self, request):
        context = {
            'today': timezone.now(),
            'user': request.user,
        }
        return render(request, self.template_name, context)

    def _resolve_cart(self, request):
        """
        Parse and validate the posted cart.
        Returns (resolved, errors) where resolved is a list of
        (product, quantity) tuples.
        Never trusts client-submitted price/name — only product_id and
        quantity are read from the client; price is always recomputed
        server-side.
        """
        try:
            cart = json.loads(request.POST.get('cart_json', '[]'))
        except (ValueError, TypeError):
            cart = []

        if not isinstance(cart, list) or not cart:
            return [], ['حداقل یک کالا باید به فاکتور اضافه شود.']

        resolved = []
        errors = []
        for line in cart:
            try:
                product_id = int(line.get('product_id'))
                qty = int(line.get('quantity', 1))
            except (TypeError, ValueError, AttributeError):
                errors.append('یکی از ردیف‌های سبد نامعتبر است.')
                continue
            if qty < 1:
                continue
            try:
                product = Product.objects.get(pk=product_id)
            except Product.DoesNotExist:
                errors.append('یکی از کالاها دیگر در سیستم موجود نیست.')
                continue
            if product.count < qty:
                errors.append(
                    f'موجودی «{product.name}» کافی نیست '
                    f'(موجودی فعلی: {product.count}).'
                )
                continue
            resolved.append((product, qty))

        if not resolved and not errors:
            errors.append('حداقل یک کالا باید به فاکتور اضافه شود.')
        return resolved, errors

    def post(self, request):
        wants_json = request.POST.get('respond_json') == '1'
        customer = request.POST.get('customer', '').strip()
        description = request.POST.get('description', '').strip()

        resolved, errors = self._resolve_cart(request)

        if errors:
            for e in errors:
                messages.error(request, e)
            if wants_json:
                return JsonResponse({'success': False, 'errors': errors}, status=400)
            context = {
                'today': timezone.now(),
                'user': request.user,
                'customer_value': customer,
                'description_value': description,
                'cart_json': request.POST.get('cart_json', '[]'),
            }
            return render(request, self.template_name, context, status=400)

        with transaction.atomic():
            faktor = FaktorSell.objects.create(
                user=request.user,
                customer=customer,
                description=description,
            )
            total = Decimal('0')
            items_payload = []
            for product, qty in resolved:
                unit_price = product.final_price_for_customer()
                FaktorItem.objects.create(
                    sell=faktor,
                    product=product,
                    quantity=qty,
                    unit_price=unit_price,
                    user=request.user,
                )
                # FIX: row-level lock prevents race condition when multiple
                # requests decrement the same product simultaneously.
                updated = Product.objects.select_for_update().filter(
                    pk=product.pk,
                    count__gte=qty,  # re-check stock inside the lock
                ).update(count=F('count') - qty)
                if not updated:
                    # Another request consumed the stock between our check
                    # and our lock — roll back the whole transaction.
                    raise ValueError(
                        f'موجودی «{product.name}» در حین ثبت تمام شد. '
                        f'لطفاً دوباره تلاش کنید.'
                    )
                line_total = unit_price * qty
                total += line_total
                items_payload.append({
                    'name': product.name,
                    'serial_number': product.serial_number,
                    'quantity': qty,
                    'unit_price': str(unit_price),
                    'total_price': str(line_total),
                })
            faktor.total_price = total
            faktor.save(update_fields=['total_price'])

        if wants_json:
            # F9 print flow: client renders the receipt from this JSON
            # and calls window.print() itself.
            return JsonResponse({
                'success': True,
                'number': faktor.number,
                'date': str(faktor.date),
                'customer': faktor.customer,
                'items': items_payload,
                'total': str(total),
            })

        messages.success(request, f'فاکتور {faktor.number} ثبت شد.')
        return redirect('faktor:sell-create')


class ListFactorSellView(StaffGroupRequiredMixin, ListView):
    model = FaktorSell
    template_name = "faktor/faktor_sell_list.html"
    context_object_name = "sells"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().filter(user=self.request.user)
        query = self.request.GET.get("q", "").strip()
        if query:
            qs = qs.filter(
                db_models.Q(customer__icontains=query)
                | db_models.Q(number__icontains=query)
            )
        return qs


class EditFaktorSellView(StaffGroupRequiredMixin, UpdateView):
    model = FaktorSell
    form_class = FaktorSellForm
    template_name = "faktor/faktor_sell_form.html"
    success_url = reverse_lazy("faktor:sell-list")

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        faktor = self.get_object()
        context['faktor'] = faktor
        context['items'] = faktor.items.all()
        context['total'] = sum(item.total_price for item in context['items'])
        context['credit'] = 0
        context['today'] = timezone.now()
        context['user'] = self.request.user
        context['description'] = faktor.description
        return context


class DeleteFaktorSellView(StaffGroupRequiredMixin, DeleteView):
    model = FaktorSell
    template_name = "faktor/faktor_sell_confirm_delete.html"
    success_url = reverse_lazy("faktor:sell-list")

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class AddItemView(StaffGroupRequiredMixin, View):
    """
    Add one unit of a product to a sell invoice.
    Accepts either an exact `barcode` (legacy scan flow) or a
    `product_id` (search-result click) — product_id is preferred.
    """

    def post(self, request):
        product_id = request.POST.get('product_id')
        barcode = request.POST.get('barcode')
        faktor_id = request.POST.get('faktor_id')

        try:
            if product_id:
                product = Product.objects.get(pk=product_id)
            else:
                product = Product.objects.get(serial_number=barcode)
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Product not found'})

        try:
            faktor = FaktorSell.objects.get(pk=faktor_id, user=request.user)
        except FaktorSell.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Faktor not found'})

        with transaction.atomic():
            item, created = FaktorItem.objects.get_or_create(
                sell=faktor,
                product=product,
                defaults={
                    'quantity': 1,
                    'unit_price': product.final_price_for_customer(),
                    'user': request.user,
                },
            )
            if not created:
                item.quantity += 1
                item.save()

            # FIX: row-level lock; also validates stock >= 1 atomically.
            updated = Product.objects.select_for_update().filter(
                pk=product.pk,
                count__gte=1,
            ).update(count=F('count') - 1)

            if not updated:
                return JsonResponse({
                    'success': False,
                    'error': f'"{product.name}" is out of stock.',
                })

        faktor.total_price = sum(i.total_price for i in faktor.items.all())
        faktor.save(update_fields=['total_price'])

        return JsonResponse({'success': True})


# ----------------------------------------------------------------------
# BUY VIEWS — temporarily disabled via BuyEnabledRequiredMixin
# ----------------------------------------------------------------------
class CreateFaktorBuyView(BuyEnabledRequiredMixin, StaffGroupRequiredMixin, CreateView):
    model = FaktorBuy
    form_class = FaktorBuyForm
    template_name = "faktor/faktor_buy_form.html"

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("faktor:buy-edit", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['faktor'] = None
        context['items'] = []
        context['total'] = 0
        context['today'] = timezone.now()
        context['user'] = self.request.user
        context['description'] = ''
        return context


class ListFactorBuyView(BuyEnabledRequiredMixin, StaffGroupRequiredMixin, ListView):
    model = FaktorBuy
    template_name = "faktor/faktor_buy_list.html"
    context_object_name = "buys"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().filter(user=self.request.user)
        query = self.request.GET.get("q", "").strip()
        if query:
            qs = qs.filter(
                db_models.Q(supplier__icontains=query)
                | db_models.Q(number__icontains=query)
            )
        return qs


class EditFaktorBuyView(BuyEnabledRequiredMixin, StaffGroupRequiredMixin, UpdateView):
    model = FaktorBuy
    form_class = FaktorBuyForm
    template_name = "faktor/faktor_buy_form.html"
    success_url = reverse_lazy("faktor:buy-list")

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        faktor = self.get_object()
        context['faktor'] = faktor
        context['items'] = faktor.items.all()
        context['total'] = sum(item.total_price for item in context['items'])
        context['today'] = timezone.now()
        context['user'] = self.request.user
        context['description'] = faktor.description
        return context


class DeleteFaktorBuyView(BuyEnabledRequiredMixin, StaffGroupRequiredMixin, DeleteView):
    model = FaktorBuy
    template_name = "faktor/faktor_buy_confirm_delete.html"
    success_url = reverse_lazy("faktor:buy-list")

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class AddBuyItemView(BuyEnabledRequiredMixin, StaffGroupRequiredMixin, View):
    """Add one unit of a product to a buy invoice."""

    def post(self, request):
        product_id = request.POST.get('product_id')
        barcode = request.POST.get('barcode')
        faktor_id = request.POST.get('faktor_id')

        try:
            if product_id:
                product = Product.objects.get(pk=product_id)
            else:
                product = Product.objects.get(serial_number=barcode)
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Product not found'})

        try:
            faktor = FaktorBuy.objects.get(pk=faktor_id, user=request.user)
        except FaktorBuy.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Faktor not found'})

        with transaction.atomic():
            item, created = FaktorItem.objects.get_or_create(
                buy=faktor,
                product=product,
                defaults={
                    'quantity': 1,
                    'unit_price': product.price_for_company,
                    'user': request.user,
                },
            )
            if not created:
                item.quantity += 1
                item.save()

            # Purchases increase stock — use F() to avoid race condition.
            Product.objects.select_for_update().filter(
                pk=product.pk
            ).update(count=F('count') + 1)

        faktor.total_price = sum(i.total_price for i in faktor.items.all())
        faktor.save(update_fields=['total_price'])

        return JsonResponse({'success': True})


# ----------------------------------------------------------------------
# REPORTS
# ----------------------------------------------------------------------
class ReportsView(StaffGroupRequiredMixin, View):
    """
    Sales dashboard.
    Cost of goods is based on current product price (not price at time of
    sale), so profit figures are approximate if prices have changed.
    """
    template_name = "faktor/reports.html"

    def get(self, request):
        from collections import defaultdict

        sell_items = FaktorItem.objects.filter(
            sell__isnull=False
        ).select_related('product', 'sell', 'sell__user')

        # ── KPIs ──────────────────────────────────────────────────────
        total_revenue = sum(i.total_price for i in sell_items)
        total_cost = sum(
            i.quantity * i.product.price_for_company for i in sell_items
        )
        total_profit = total_revenue - total_cost

        total_invoices = FaktorSell.objects.count()
        total_items_sold = sum(i.quantity for i in sell_items)

        # ── Daily sales — last 30 days ────────────────────────────────
        since = timezone.now().date() - timedelta(days=29)
        daily_map = defaultdict(float)
        for item in sell_items:
            if item.sell.date >= since:
                daily_map[str(item.sell.date)] += float(item.total_price)

        daily_labels, daily_values = [], []
        for d in range(30):
            day = since + timedelta(days=d)
            daily_labels.append(str(day))
            daily_values.append(round(daily_map.get(str(day), 0)))

        # ── Monthly sales — last 6 months ─────────────────────────────
        six_months_ago = timezone.now().date().replace(day=1) - timedelta(days=150)
        monthly_map = defaultdict(float)
        for item in sell_items:
            if item.sell.date >= six_months_ago:
                key = item.sell.date.strftime("%Y-%m")
                monthly_map[key] += float(item.total_price)

        monthly_labels = sorted(monthly_map.keys())
        monthly_values = [round(monthly_map[k]) for k in monthly_labels]

        # ── Top 10 products by revenue ────────────────────────────────
        product_map = defaultdict(lambda: {"revenue": 0.0, "qty": 0})
        for item in sell_items:
            name = item.product.name
            product_map[name]["revenue"] += float(item.total_price)
            product_map[name]["qty"] += item.quantity

        top_products = sorted(
            product_map.items(), key=lambda x: x[1]["revenue"], reverse=True
        )[:10]
        top_product_labels = [p[0] for p in top_products]
        top_product_values = [round(p[1]["revenue"]) for p in top_products]
        top_product_qty = [p[1]["qty"] for p in top_products]

        # ── Category (tag) distribution ───────────────────────────────
        tag_map = defaultdict(float)
        for item in sell_items:
            tag = item.product.tag or "سایر"
            tag_map[tag] += float(item.total_price)

        tag_labels = list(tag_map.keys())
        tag_values = [round(v) for v in tag_map.values()]

        # ── Profit margin per product (top 8) ────────────────────────
        margin_map = defaultdict(list)
        for item in sell_items:
            cost = float(item.product.price_for_company)
            if cost > 0:
                margin = ((float(item.unit_price) - cost) / cost) * 100
                margin_map[item.product.name].append(round(margin, 1))

        avg_margin = {k: round(sum(v) / len(v), 1) for k, v in margin_map.items()}
        top_margin = sorted(avg_margin.items(), key=lambda x: x[1], reverse=True)[:8]
        margin_labels = [x[0] for x in top_margin]
        margin_values = [x[1] for x in top_margin]

        # ── Last 10 invoices ──────────────────────────────────────────
        recent_invoices = FaktorSell.objects.order_by('-date', '-id')[:10]

        context = {
            # KPIs
            "total_revenue": total_revenue,
            "total_cost": total_cost,
            "total_profit": total_profit,
            "total_invoices": total_invoices,
            "total_items_sold": total_items_sold,
            "profit_margin_pct": round(
                (float(total_profit) / float(total_revenue) * 100)
                if total_revenue else 0,
                1,
            ),
            # Charts
            "daily_labels": daily_labels,
            "daily_values": daily_values,
            "monthly_labels": monthly_labels,
            "monthly_values": monthly_values,
            "top_product_labels": top_product_labels,
            "top_product_values": top_product_values,
            "top_product_qty": top_product_qty,
            "tag_labels": tag_labels,
            "tag_values": tag_values,
            "margin_labels": margin_labels,
            "margin_values": margin_values,
            # Table
            "recent_invoices": recent_invoices,
        }
        return render(request, self.template_name, context)

