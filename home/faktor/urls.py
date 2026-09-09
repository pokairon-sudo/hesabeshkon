
# faktor/urls.py
from django.urls import path
from .views import (
    CreateFaktorSellView,
    ListFactorSellView,
    EditFaktorSellView,
    DeleteFaktorSellView,
    AddItemView,
    CreateFaktorBuyView,
    ListFactorBuyView,
    EditFaktorBuyView,
    DeleteFaktorBuyView,
    AddBuyItemView,
    SearchProductsView,
)

app_name = "faktor"

urlpatterns = [
    # ---------- SELL ----------
    path(
        "sell/create/",
        CreateFaktorSellView.as_view(),
        name="sell-create",
    ),
    path(
        "sell/list/",
        ListFactorSellView.as_view(),
        name="sell-list",
    ),
    path(
        "sell/edit/<int:pk>/",
        EditFaktorSellView.as_view(),
        name="sell-edit",
    ),
    path(
        "sell/delete/<int:pk>/",
        DeleteFaktorSellView.as_view(),
        name="sell-delete",
    ),

    # ---------- ITEMS ----------
    path(
        "item/add/",
        AddItemView.as_view(),
        name="add-item",
    ),
    path(
        "products/search/",
        SearchProductsView.as_view(),
        name="search-products",
    ),

    # ---------- BUY ----------
    path(
        "buy/create/",
        CreateFaktorBuyView.as_view(),
        name="buy-create",
    ),
    path(
        "buy/list/",
        ListFactorBuyView.as_view(),
        name="buy-list",
    ),
    path(
        "buy/edit/<int:pk>/",
        EditFaktorBuyView.as_view(),
        name="buy-edit",
    ),
    path(
        "buy/delete/<int:pk>/",
        DeleteFaktorBuyView.as_view(),
        name="buy-delete",
    ),
    path(
        "buy-item/add/",
        AddBuyItemView.as_view(),
        name="add-buy-item",
    ),
]
