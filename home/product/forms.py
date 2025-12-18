
# forms.py
from django import forms
from .models import Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "tag",
            "serial_number",
            "price_for_company",
            "price_for_customer",
            "count",
            "offer_value",
            "offer_type",
        ]
        widgets = {
            "offer_value": forms.NumberInput(attrs={"step": "0.01"}),
            "offer_type": forms.Select(),
        }
        labels = {
            "offer_value": "Offer amount",
            "offer_type": "Offer type",
        }
        help_texts = {
            "offer_value": "Enter a number – e.g. 10 for 10 % or 15 for $15 discount",
            "offer_type": "Choose whether the number is a percentage or a fixed price",
        }

# from django import forms
# from .models import Product
#
#
# class ProductForm(forms.ModelForm):
#     class Meta:
#         model = Product
#         fields = [
#             "name",
#             "tag",
#             "serial_number",
#             "price_for_company",
#             "price_for_customer",
#             "count",
#             "offer",
#         ]
