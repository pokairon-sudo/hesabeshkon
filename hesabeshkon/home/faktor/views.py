
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
from accounts.mixins import StaffGroupRequiredMixin  # T2.1: faktor/invoicing is staff-only
from django.contrib import messages
from django.db.models import Sum, F, DecimalField
from django.db.models.functions import Coalesce
from datetime import timedelta

from .models import FaktorSell, FaktorBuy, FaktorItem
from .forms import FaktorSellForm, FaktorBuyForm
from product.models import Product


class BuyEnabledRequiredMixin:
    """
    #4: buy invoices are temporarily disabled. Every buy view checks this
    first (before the staff-group check even runs), so a disabled feature
    fails with a clear message instead of a confusing 403 or a working page
    nobody's supposed to use yet. Flip settings.FAKTOR_BUY_ENABLED back to
    True to restore access — nothing else needs to change.
    """

    def dispatch(self, request, *args, **kwargs):
        if not getattr(settings, "FAKTOR_BUY_ENABLED", True):
            messages.error(request, "Buy invoices are temporarily disabled.")
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)


# ----------------------------------------------------------------------
# SEARCH (shared by sell + buy) — #3/#6
# ----------------------------------------------------------------------
class SearchProductsView(StaffGroupRequiredMixin, View):
    """
    Live product search by barcode (serial_number), name, or tag — used by
    the invoice item-entry panel so staff aren't limited to scanning an
    exact barcode. Returns JSON; the invoice-form JS renders a dropdown.
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
    #1/#2/#3 rework: the previous flow saved an EMPTY FaktorSell row the
    moment this page was even opened (needed a faktor_id to add items
    against), then redirected to /edit/<pk>/ to actually build the
    invoice — meaning junk empty invoices could pile up in the DB just
    from opening this page, and closing an invoice always bounced through
    an /edit/ URL.

    Now: nothing touches the database on GET. Scanned items live in a
    client-side cart (JS) built by looking products up read-only via
    SearchProductsView. The entire invoice — customer/description + every
    item — is submitted in ONE POST when F7/F8/F9 is pressed, and is
    created atomically:
      - an empty cart is rejected (#2: never saves an empty invoice)
      - the invoice number is assigned by the model at the moment of that
        one real save (#1: "auto serial" — nothing to do manually)
      - success always returns to THIS SAME page, fresh and empty
        (#3: never redirects to /edit/<pk>/)
    """
    template_name = "faktor/faktor_sell_create.html"

    def get(self, request):
        context = {
            'today': timezone.now(),
            'user': request.user,
        }
        return render(request, self.template_name, context)

    def _resolve_cart(self, request):
        """Parse+validate the posted cart. Returns (resolved, errors) where
        resolved is a list of (product, quantity) and errors is a list of
        user-facing strings. Never trusts client-submitted price/name —
        only product_id and quantity are read from the client; price is
        always recomputed server-side from the product's current price."""
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
                    f'موجودی «{product.name}» کافی نیست (موجودی فعلی: {product.count}).'
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
                user=request.user, customer=customer, description=description,
            )
            total = Decimal('0')
            items_payload = []
            for product, qty in resolved:
                unit_price = product.final_price_for_customer()
                FaktorItem.objects.create(
                    sell=faktor, product=product, quantity=qty,
                    unit_price=unit_price, user=request.user,
                )
                product.count -= qty
                product.save(update_fields=['count'])
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
            # #F9 print flow: the client renders the receipt from this JSON
            # and calls window.print() itself, then navigates back here —
            # there's no server-rendered "saved invoice" page to print from
            # anymore, since we never redirect through /edit/.
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
            # T1.6: search box previously submitted `?q=` but nothing read it.
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
        # T1.1 bug fix: this context never actually exposed `faktor` itself,
        # only derived values — so `data-faktor-id="{{ faktor.pk }}"` in the
        # template always rendered empty and the barcode-scan JS silently
        # refused to add items ("Please save the faktor first.") even on
        # an already-saved invoice.
        context['faktor'] = faktor
        context['items'] = faktor.items.all()
        context['total'] = sum(item.total_price for item in context['items'])
        context['credit'] = 0  # Placeholder
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
    Add one unit of a product to a sell invoice. #3: accepts either an
    exact `barcode` (legacy scan-and-Enter flow) or a `product_id` (new
    click-a-search-result flow) — product_id is preferred when present
    since it can't collide/mismatch the way a re-typed barcode string can.
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

        # T1.4: don't let a sale push stock below zero.
        if product.count <= 0:
            return JsonResponse({
                'success': False,
                'error': f'"{product.name}" is out of stock.',
            })

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

        # T1.4: decrement stock by exactly the one unit just sold.
        product.count -= 1
        product.save(update_fields=['count'])

        # Update total_price
        faktor.total_price = sum(i.total_price for i in faktor.items.all())
        faktor.save()

        return JsonResponse({'success': True})


# ----------------------------------------------------------------------
# BUY VIEWS — #4: temporarily disabled via BuyEnabledRequiredMixin
# ----------------------------------------------------------------------
class CreateFaktorBuyView(BuyEnabledRequiredMixin, StaffGroupRequiredMixin, CreateView):
    model = FaktorBuy
    form_class = FaktorBuyForm
    template_name = "faktor/faktor_buy_form.html"

    def form_valid(self, form):
        # T1.7: buy invoices are now scoped per-user, same as sell.
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
        # T1.7: buy invoices scoped to the user who created them, same
        # policy as sell. (Rows created before this field existed have a
        # null user and simply won't show up per-user — see roadmap T1.7
        # if you'd rather buy invoices be shared/company-wide instead.)
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
    """Add one unit of a product to a buy invoice. T1.2/T1.4, #3/#6 search."""

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

        # T1.4: purchases increase stock.
        product.count += 1
        product.save(update_fields=['count'])

        faktor.total_price = sum(i.total_price for i in faktor.items.all())
        faktor.save()

        return JsonResponse({'success': True})

# home/faktor/views.py
# فقط ReportsView رو جایگزین کن — بقیه views دست نخور

class ReportsView(StaffGroupRequiredMixin, View):
    """
    داشبورد گزارشات فروش.
    - بهای تمام‌شده بر اساس قیمت فعلی محصول محاسبه می‌شه (نه قیمت زمان فروش)
    - اگه قیمت‌ها تغییر کرده باشن، سود تقریبیه
    """
    template_name = "faktor/reports.html"

    def get(self, request):
        from django.db.models import Sum, Count, F, Q
        from django.utils import timezone
        from datetime import timedelta
        from collections import defaultdict

        sell_items = FaktorItem.objects.filter(
        sell__isnull=False
        ).select_related('product', 'sell', 'sell__user')


        # ── KPI اصلی ──────────────────────────────────────────────
        total_revenue = sum(i.total_price for i in sell_items)
        total_cost    = sum(
            i.quantity * i.product.price_for_company for i in sell_items
        )
        total_profit  = total_revenue - total_cost

        # ── تعداد کل فاکتور و آیتم ────────────────────────────────
        total_invoices = FaktorSell.objects.count()
        total_items_sold = sum(i.quantity for i in sell_items)

        # ── فروش روزانه ۳۰ روز اخیر ──────────────────────────────
        since = timezone.now().date() - timedelta(days=29)
        daily_map = defaultdict(float)
        for item in sell_items:
            if item.sell.date >= since:
                daily_map[str(item.sell.date)] += float(item.total_price)

        # پر کردن روزهای بدون فروش با صفر
        daily_labels, daily_values = [], []
        for d in range(30):
            day = since + timedelta(days=d)
            daily_labels.append(str(day))
            daily_values.append(round(daily_map.get(str(day), 0)))

        # ── فروش ماهانه ۶ ماه اخیر ───────────────────────────────
        six_months_ago = timezone.now().date().replace(day=1) - timedelta(days=150)
        monthly_map = defaultdict(float)
        for item in sell_items:
            if item.sell.date >= six_months_ago:
                key = item.sell.date.strftime("%Y-%m")
                monthly_map[key] += float(item.total_price)

        monthly_labels = sorted(monthly_map.keys())
        monthly_values = [round(monthly_map[k]) for k in monthly_labels]

        # ── پرفروش‌ترین محصولات (top 10) ──────────────────────────
        product_map = defaultdict(lambda: {"revenue": 0.0, "qty": 0})
        for item in sell_items:
            name = item.product.name
            product_map[name]["revenue"] += float(item.total_price)
            product_map[name]["qty"]     += item.quantity

        top_products = sorted(
            product_map.items(), key=lambda x: x[1]["revenue"], reverse=True
        )[:10]
        top_product_labels = [p[0] for p in top_products]
        top_product_values = [round(p[1]["revenue"]) for p in top_products]
        top_product_qty    = [p[1]["qty"] for p in top_products]

        # ── توزیع دسته‌بندی (tag) ──────────────────────────────────
        tag_map = defaultdict(float)
        for item in sell_items:
            tag = item.product.tag or "سایر"
            tag_map[tag] += float(item.total_price)

        tag_labels = list(tag_map.keys())
        tag_values = [round(v) for v in tag_map.values()]

        # ── نرخ سود هر محصول (top 8) ─────────────────────────────
        margin_data = []
        for item in sell_items:
            cost = float(item.product.price_for_company)
            if cost > 0:
                margin = ((float(item.unit_price) - cost) / cost) * 100
                margin_data.append((item.product.name, round(margin, 1)))

        # میانگین margin هر محصول
        margin_map = defaultdict(list)
        for name, m in margin_data:
            margin_map[name].append(m)
        avg_margin = {k: round(sum(v)/len(v), 1) for k, v in margin_map.items()}
        top_margin = sorted(avg_margin.items(), key=lambda x: x[1], reverse=True)[:8]
        margin_labels = [x[0] for x in top_margin]
        margin_values = [x[1] for x in top_margin]

        # ── آخرین ۱۰ فاکتور ───────────────────────────────────────
        recent_invoices = FaktorSell.objects.order_by('-date', '-id')[:10]

        context = {
            # KPI
            "total_revenue":     total_revenue,
            "total_cost":        total_cost,
            "total_profit":      total_profit,
            "total_invoices":    total_invoices,
            "total_items_sold":  total_items_sold,
            "profit_margin_pct": round(
                (float(total_profit) / float(total_revenue) * 100)
                if total_revenue else 0, 1
            ),
            # نمودارها
            "daily_labels":        daily_labels,
            "daily_values":        daily_values,
            "monthly_labels":      monthly_labels,
            "monthly_values":      monthly_values,
            "top_product_labels":  top_product_labels,
            "top_product_values":  top_product_values,
            "top_product_qty":     top_product_qty,
            "tag_labels":          tag_labels,
            "tag_values":          tag_values,
            "margin_labels":       margin_labels,
            "margin_values":       margin_values,
            # جدول آخرین فاکتورها
            "recent_invoices":     recent_invoices,
        }
        return render(request, self.template_name, context)

