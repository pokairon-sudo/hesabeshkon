from django.urls import path
from .views import (
    HomePage,
    PosComingSoonView,
    CalculatorComingSoonView,
    ConverterComingSoonView,
    ScaleSettingsComingSoonView,
    TelegramSettingsComingSoonView,
)

urlpatterns = [
    path('', HomePage.as_view(), name='home'),
    path('pos/', PosComingSoonView.as_view(), name='pos'),
    path('calculator/', CalculatorComingSoonView.as_view(), name='calculator'),
    path('converter/', ConverterComingSoonView.as_view(), name='converter'),
    path('settings/scale/', ScaleSettingsComingSoonView.as_view(), name='scale-settings'),
    path('settings/telegram/', TelegramSettingsComingSoonView.as_view(), name='telegram-settings'),
]
