from django.urls import path

from .views import (
    AddItemView,
    BuyDeleteView,
    BuyInvoiceView,
    BuyListView,
    BuyPreviewView,
    OCRConfirmView,
    OCRUploadView,
    SearchProductsView,
    SellDeleteView,
    SellInvoiceView,
    SellListView,
    SellPreviewView,
)

app_name = "faktor"

urlpatterns = [
    # فروش
    path("sell/new/", SellInvoiceView.as_view(), name="sell-create"),
    path("sell/list/", SellListView.as_view(), name="sell-list"),
    path("sell/<int:pk>/edit/", SellInvoiceView.as_view(), name="sell-edit"),
    path("sell/<int:pk>/delete/", SellDeleteView.as_view(), name="sell-delete"),
    path("sell/<int:pk>/", SellPreviewView.as_view(), name="sell-preview"),
    # خرید
    path("buy/new/", BuyInvoiceView.as_view(), name="buy-create"),
    path("buy/list/", BuyListView.as_view(), name="buy-list"),
    path("buy/<int:pk>/edit/", BuyInvoiceView.as_view(), name="buy-edit"),
    path("buy/<int:pk>/delete/", BuyDeleteView.as_view(), name="buy-delete"),
    path("buy/<int:pk>/", BuyPreviewView.as_view(), name="buy-preview"),
    path("buy/ocr/", OCRUploadView.as_view(), name="ocr"),
    path("buy/ocr/confirm/", OCRConfirmView.as_view(), name="ocr-confirm"),
    # API
    path("products/search/", SearchProductsView.as_view(), name="search-products"),
    path("item/add/", AddItemView.as_view(), name="add-item"),
]
