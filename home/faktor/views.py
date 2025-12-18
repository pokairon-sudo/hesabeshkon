
# faktor/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DeleteView,
)
from django.http import JsonResponse
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from .models import FaktorSell, FaktorBuy, FaktorItem
from .forms import FaktorSellForm, FaktorBuyForm
from product.models import Product


# ----------------------------------------------------------------------
# SELL VIEWS
# ----------------------------------------------------------------------
class CreateFaktorSellView(LoginRequiredMixin, CreateView):
    model = FaktorSell
    form_class = FaktorSellForm
    template_name = "faktor/faktor_sell_form.html"
    success_url = reverse_lazy("faktor:sell-list")

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class ListFactorSellView(LoginRequiredMixin, ListView):
    model = FaktorSell
    template_name = "faktor/faktor_sell_list.html"
    context_object_name = "sells"
    paginate_by = 20  # optional

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class EditFaktorSellView(LoginRequiredMixin, UpdateView):
    model = FaktorSell
    form_class = FaktorSellForm
    template_name = "faktor/faktor_sell_form.html"
    success_url = reverse_lazy("faktor:sell-list")

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        faktor = self.get_object()
        context['items'] = faktor.items.all()
        context['total'] = sum(item.total_price for item in context['items'])
        context['credit'] = 0  # Placeholder
        context['today'] = timezone.now()
        context['user'] = self.request.user
        context['description'] = faktor.description
        return context


class DeleteFaktorSellView(LoginRequiredMixin, DeleteView):
    model = FaktorSell
    template_name = "faktor/faktor_sell_confirm_delete.html"
    success_url = reverse_lazy("faktor:sell-list")

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class AddItemView(LoginRequiredMixin, View):
    def post(self, request):
        barcode = request.POST.get('barcode')
        faktor_id = request.POST.get('faktor_id')

        try:
            product = Product.objects.get(serial_number=barcode)
            faktor = FaktorSell.objects.get(pk=faktor_id, user=request.user)
            item, created = FaktorItem.objects.get_or_create(
                sell=faktor,
                product=product,
                defaults={
                    'quantity': 1,
                    'unit_price': product.final_price_for_customer(),
                    'user': request.user
                }
            )
            if not created:
                item.quantity += 1
                item.save()

            # Update total_price
            faktor.total_price = sum(item.total_price for item in faktor.items.all())
            faktor.save()

            return JsonResponse({'success': True})
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Product not found'})
        except FaktorSell.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Faktor not found'})


# ----------------------------------------------------------------------
# BUY VIEWS
# ----------------------------------------------------------------------
class CreateFaktorBuyView(CreateView):
    model = FaktorBuy
    form_class = FaktorBuyForm
    template_name = "faktor/faktor_buy_form.html"
    success_url = reverse_lazy("faktor:buy-list")


class ListFactorBuyView(ListView):
    model = FaktorBuy
    template_name = "faktor/faktor_buy_list.html"
    context_object_name = "buys"
    paginate_by = 20


class EditFaktorBuyView(UpdateView):
    model = FaktorBuy
    form_class = FaktorBuyForm
    template_name = "faktor/faktor_buy_form.html"
    success_url = reverse_lazy("faktor:buy-list")


class DeleteFaktorBuyView(DeleteView):
    model = FaktorBuy
    template_name = "faktor/faktor_buy_confirm_delete.html"
    success_url = reverse_lazy("faktor:buy-list")
# from django.shortcuts import render
#
# # Create your views here.
#
#
# class CreateFaktorSellView():
#
#
#     def get(self,request):
#         pass
#
#     def post(self,request):
#         pass 
#
#
# class ListFactorSellView():
#
#
#     def get(self,request):
#         pass
#
#     def post(self,request):
#         pass 
#
#
# class DeleteFaktorSellView():
#
#
#     def get(self,request):
#         pass
#
#     def post(self,request):
#         pass 
#
#
# class EditFaktorSellView():
#
#
#     def get(self,request):
#         pass
#
#     def post(self,request):
#         pass 
#
#
# class CreateFaktorBuyView():
#
#
#     def get(self,request):
#         pass
#
#     def post(self,request):
#         pass 
#
#
# class ListFactorBuyView():
#
#
#
#     def get(self,request):
#         pass
#
#     def post(self,request):
#         pass 
#
#
# class DeleteFaktorBuyView():
#
#
#     def get(self,request):
#         pass
#
#     def post(self,request):
#         pass 
#
#
# class EditFaktorBuyView():
#
#
#     def get(self,request):
#         pass
#
#     def post(self,request):
#         pass 
#

