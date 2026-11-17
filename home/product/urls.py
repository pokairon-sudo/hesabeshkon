from django.urls import path

from .views import (
    BarcodeLookupView,
    CreateProductView,
    DeleteProductView,
    EditProductView,
    ExportProductsView,
    NewBarcodeView,
    ProductDetailView,
    ProductListView,
)

app_name = "product"

urlpatterns = [
    path("", ProductListView.as_view(), name="l-product"),
    path("new/", CreateProductView.as_view(), name="c-product"),
    path("new/barcode/", NewBarcodeView.as_view(), name="new-barcode"),
    path("<int:pk>/edit/", EditProductView.as_view(), name="e-product"),
    path("<int:pk>/delete/", DeleteProductView.as_view(), name="d-product"),
    path("<int:pk>/json/", ProductDetailView.as_view(), name="detail"),
    path("by-barcode/<str:barcode>/", BarcodeLookupView.as_view(), name="by-barcode"),
    path("export/", ExportProductsView.as_view(), name="export"),
]
