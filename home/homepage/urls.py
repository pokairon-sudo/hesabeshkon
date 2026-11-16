from django.urls import path

from .views import HomePage, TelegramComingSoonView

urlpatterns = [
    path("", HomePage.as_view(), name="home"),
    path("telegram/", TelegramComingSoonView.as_view(), name="telegram-settings"),
]
