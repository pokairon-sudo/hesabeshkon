import logging

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View

from accounts.mixins import AdminRequiredMixin
from faktor.models import FaktorBuy, FaktorSell

from .forms import ShopSettingsForm
from .models import ShopSettings

logger = logging.getLogger("accounting")


class SettingsView(AdminRequiredMixin, View):
    template_name = "core/settings.html"

    def get(self, request):
        shop = ShopSettings.load()
        return render(
            request,
            self.template_name,
            {
                "form": ShopSettingsForm(instance=shop),
                "shop": shop,
                "unaccounted_sell": FaktorSell.objects.filter(
                    status=FaktorSell.Status.COMPLETED, accounted=False
                ).count(),
                "unaccounted_buy": FaktorBuy.objects.filter(
                    status=FaktorBuy.Status.COMPLETED, accounted=False
                ).count(),
            },
        )

    def post(self, request):
        shop = ShopSettings.load()
        form = ShopSettingsForm(request.POST, instance=shop)
        if form.is_valid():
            shop = form.save()
            messages.success(request, "تنظیمات ذخیره شد.")
            return redirect("settings")
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "shop": shop,
                "unaccounted_sell": FaktorSell.objects.filter(
                    status=FaktorSell.Status.COMPLETED, accounted=False
                ).count(),
                "unaccounted_buy": FaktorBuy.objects.filter(
                    status=FaktorBuy.Status.COMPLETED, accounted=False
                ).count(),
            },
            status=400,
        )


class SyncAccountantView(AdminRequiredMixin, View):
    """ارسال دوباره‌ی فاکتورهای نهایی‌شده‌ای که در دیتابیس حسابدار ثبت نشده‌اند."""

    def post(self, request):
        from accounting.services import AccountantUnavailable, post_buy, post_sell

        sell_qs = FaktorSell.objects.filter(status=FaktorSell.Status.COMPLETED, accounted=False)
        buy_qs = FaktorBuy.objects.filter(status=FaktorBuy.Status.COMPLETED, accounted=False)
        ok, failed = 0, 0
        for invoice in sell_qs:
            try:
                post_sell(invoice)
                ok += 1
            except AccountantUnavailable as exc:
                failed += 1
                logger.warning("sync sell %s failed: %s", invoice.pk, exc)
            except Exception as exc:  # noqa: BLE001
                failed += 1
                logger.exception("sync sell %s failed: %s", invoice.pk, exc)
        for invoice in buy_qs:
            try:
                post_buy(invoice)
                ok += 1
            except AccountantUnavailable as exc:
                failed += 1
                logger.warning("sync buy %s failed: %s", invoice.pk, exc)
            except Exception as exc:  # noqa: BLE001
                failed += 1
                logger.exception("sync buy %s failed: %s", invoice.pk, exc)

        if ok:
            messages.success(request, f"{ok} فاکتور با موفقیت به دیتابیس حسابدار ارسال شد.")
        if failed:
            messages.error(
                request,
                f"{failed} فاکتور ارسال نشد. مطمئن شوید «migrate --database=accountant» اجرا شده است.",
            )
        if not ok and not failed:
            messages.info(request, "فاکتور ارسال‌نشده‌ای وجود ندارد.")
        return redirect("settings")
