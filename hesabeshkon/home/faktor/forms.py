
# faktor/forms.py
from django import forms
from .models import FaktorSell, FaktorBuy


class FaktorSellForm(forms.ModelForm):
    class Meta:
        model = FaktorSell
        # T1.1: `customer` and `description` were missing here, so the
        # customer-name input and the hidden description field on the sell
        # form both posted data that Django silently discarded (ModelForm
        # only binds declared fields). total_price stays included because
        # the hidden field in the template sends the client-computed total.
        fields = ["customer", "description", "total_price"]
        widgets = {
            "total_price": forms.HiddenInput(),
            "description": forms.HiddenInput(),
        }


class FaktorBuyForm(forms.ModelForm):
    class Meta:
        model = FaktorBuy
        # T1.2: mirrors FaktorSellForm — supplier/description are now real
        # bound fields instead of silently-dropped POST data.
        fields = ["supplier", "description", "total_price"]
        widgets = {
            "total_price": forms.HiddenInput(),
            "description": forms.HiddenInput(),
        }
