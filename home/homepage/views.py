from django.conf import settings
from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
# Create your views here.


class HomePage(View):
    """
    #1/#2: this page is now the app's single navigation hub — buttons/tiles
    for every section, instead of a persistent top navbar. Anonymous users
    see a login/register prompt instead of the tile grid.
    """
    template_name = 'index.html'

    def get(self, request):
        context = {
            'buy_enabled': getattr(settings, 'FAKTOR_BUY_ENABLED', True),
        }
        return render(request, self.template_name, context)


class ComingSoonView(LoginRequiredMixin, View):
    """
    Placeholder for dashboard tiles that don't have a real feature behind
    them yet (POS, calculator, unit converter, scale integration, Telegram
    integration). Each is its own real feature that needs its own scoping —
    this just avoids a dead 404 link from the dashboard in the meantime.
    """
    template_name = 'coming_soon.html'
    title = "به زودی"
    description = ""

    def get(self, request):
        return render(request, self.template_name, {
            'title': self.title,
            'description': self.description,
        })


class PosComingSoonView(ComingSoonView):
    title = "صندوق فروش (POS)"
    description = "صفحه فروش سریع با اسکن بارکد و پرداخت آنی — هنوز ساخته نشده."


class CalculatorComingSoonView(ComingSoonView):
    title = "ماشین حساب"
    description = "ماشین حساب داخلی برای محاسبات سریع — هنوز ساخته نشده."


class ConverterComingSoonView(ComingSoonView):
    title = "تبدیل واحد"
    description = "ابزار تبدیل واحد (وزن، ارز و ...) — هنوز ساخته نشده."


class ScaleSettingsComingSoonView(ComingSoonView):
    title = "تنظیمات باسکول/ترازو"
    description = "اتصال به دستگاه توزین برای دریافت وزن مستقیم — هنوز ساخته نشده."


class TelegramSettingsComingSoonView(ComingSoonView):
    title = "تنظیمات تلگرام"
    description = "اتصال ربات تلگرام برای اعلان سفارش/فاکتور — هنوز ساخته نشده."
