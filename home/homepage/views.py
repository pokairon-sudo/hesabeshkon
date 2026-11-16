from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from django.views.generic import TemplateView

from accounts.mixins import AppAccessRequiredMixin
from core.models import ShopSettings
from faktor.models import FaktorBuy, FaktorItem, FaktorSell, InvoiceStatus
from product.models import Product


class HomePage(AppAccessRequiredMixin, TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.localdate()
        month_start = today - timedelta(days=29)
        shop = ShopSettings.load()

        sells = FaktorSell.objects.filter(status=InvoiceStatus.COMPLETED)
        drafts = FaktorSell.objects.filter(status=InvoiceStatus.DRAFT)
        buys = FaktorBuy.objects.filter(status=InvoiceStatus.COMPLETED)
        if not user.is_admin:
            sells = sells.filter(user=user)
            drafts = drafts.filter(user=user)
            buys = buys.filter(user=user)

        today_sales = sells.filter(date=today).aggregate(total=Sum("total_price"))["total"] or Decimal("0")
        month_sales = sells.filter(date__gte=month_start).aggregate(total=Sum("total_price"))["total"] or Decimal(
            "0"
        )

        month_items = FaktorItem.objects.filter(sell__in=sells, sell__date__gte=month_start)
        month_profit = sum((item.profit for item in month_items), Decimal("0"))
        today_items = FaktorItem.objects.filter(sell__in=sells, sell__date=today)
        today_profit = sum((item.profit for item in today_items), Decimal("0"))

        low_stock = Product.objects.filter(is_active=True, count__lte=shop.low_stock_threshold).order_by("count")[:6]
        context.update(
            {
                "today_sales": today_sales,
                "month_sales": month_sales,
                "today_profit": today_profit,
                "month_profit": month_profit,
                "today_invoices": sells.filter(date=today).count(),
                "month_invoices": sells.filter(date__gte=month_start).count(),
                "draft_count": drafts.count(),
                "draft_invoices": drafts.select_related("user").order_by("-updated_at")[:6],
                "low_stock": low_stock,
                "low_stock_count": Product.objects.filter(
                    is_active=True, count__lte=shop.low_stock_threshold
                ).count(),
                "product_count": Product.objects.filter(is_active=True).count(),
                "unaccounted": (
                    FaktorSell.objects.filter(status=InvoiceStatus.COMPLETED, accounted=False).count()
                    + FaktorBuy.objects.filter(status=InvoiceStatus.COMPLETED, accounted=False).count()
                )
                if user.is_admin
                else 0,
                "buy_total_month": buys.filter(date__gte=month_start).aggregate(total=Sum("total_price"))["total"]
                or Decimal("0"),
            }
        )
        return context


class ComingSoonView(AppAccessRequiredMixin, TemplateView):
    template_name = "coming_soon.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("title", "به زودی")
        context.setdefault("description", "این بخش هنوز آماده نشده است.")
        return context


class TelegramComingSoonView(ComingSoonView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "اتصال تلگرام"
        context["description"] = (
            "ربات تلگرام برای اعلان فروش/موجودی در نقشه‌ی راه است و فعلاً غیرفعال است."
        )
        return context

