
from django.urls import path
from .views import (
    CreateProductView,
    ListProductView,
    DeleteProductView,
    EditProductView,
)

app_name = "product" 
urlpatterns = [
    path('create/', CreateProductView.as_view(), name='c-product'),
    path('list/', ListProductView.as_view(), name='l-product'),
    path('delete/<int:pk>/', DeleteProductView.as_view(), name='d-product'),
    path('edit/<int:pk>/', EditProductView.as_view(), name='e-product'),
]
