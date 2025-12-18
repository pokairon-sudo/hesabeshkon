from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib import messages
from .forms import ProductForm
from .models import Product
from django.urls import reverse_lazy
from django.views.generic import UpdateView
# Create your views here.


class CreateProductView(View):
    def get(self, request):
        form = ProductForm()
        return render(request, "product/create.html", {"form": form})

    def post(self, request):
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your product successfuly added .")
            return redirect("c-product")
        messages.error(request, "Your form for product is invalid.")
        return render(request, "product/create.html", {"form": form})


class ListProductView(View):
    """List products with optional search by name or serial number."""
    def get(self, request):
        query = request.GET.get("q", "").strip()
        filter_by = request.GET.get("field", "name")   # default search field

        if query:
            if filter_by == "serial":
                products = Product.objects.filter(serial_number__icontains=query)
            else:   # name
                products = Product.objects.filter(name__icontains=query)
        else:
            products = Product.objects.all()

        context = {
            "products": products,
            "query": query,
            "filter_by": filter_by,
        }
        return render(request, "product/list.html", context)



class DeleteProductView(View):
    """
    Delete a product directly on POST.
    The view expects a POST request (e.g., from a form or a button).
    After deletion a success message is added and the user is sent back
    to the product list.
    """

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.delete()
        messages.success(request, f'Product “{product.name}” was deleted.')
        return redirect("l-product")




class EditProductView(View):
    """Display a form pre‑filled with the product data and save changes."""

    template_name = "product/edit.html"

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        form = ProductForm(instance=product)
        return render(request, self.template_name, {"form": form, "product": product})

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request,'your product edited successfuly')
            return redirect("l-product")          # back to the list view
        # if the form is invalid, re‑render with errors
        messages.error(request,'your form is invalid ')
        return render(request, self.template_name, {"form": form, "product": product})

