from django.urls import path

from .views import SettingsView, SyncAccountantView

urlpatterns = [
    path("", SettingsView.as_view(), name="settings"),
    path("sync-accountant/", SyncAccountantView.as_view(), name="sync-accountant"),
]
