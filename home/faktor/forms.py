
# faktor/forms.py
from django import forms
from .models import FaktorSell, FaktorBuy


class FaktorSellForm(forms.ModelForm):
    class Meta:
        model = FaktorSell
        fields = ["total_price"]


class FaktorBuyForm(forms.ModelForm):
    class Meta:
        model = FaktorBuy
        fields = ["total_price"]
