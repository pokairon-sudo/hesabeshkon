from django.contrib import admin
from django.urls import include, path

from faktor.views import ReportsExportView, ReportsView

admin.site.site_header = "حساب‌شکن — پنل مدیریت"
admin.site.site_title = "حساب‌شکن"
admin.site.index_title = "مدیریت داده‌ها و دسترسی‌ها"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("product/", include("product.urls")),
    path("faktor/", include("faktor.urls")),
    path("settings/", include("core.urls")),
    path("reports/", ReportsView.as_view(), name="reports"),
    path("reports/export/", ReportsExportView.as_view(), name="reports-export"),
    path("", include("homepage.urls")),
]
