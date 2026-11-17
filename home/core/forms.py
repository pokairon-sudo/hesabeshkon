from django import forms

from .models import ShopSettings


class ShopSettingsForm(forms.ModelForm):
    class Meta:
        model = ShopSettings
        fields = [
            "shop_name",
            "phone",
            "address",
            "currency_unit",
            "show_usd",
            "usd_rate",
            "default_markup_percent",
            "low_stock_threshold",
            "receipt_footer",
        ]
        widgets = {
            "shop_name": forms.TextInput(attrs={"class": "brut-input"}),
            "phone": forms.TextInput(attrs={"class": "brut-input", "dir": "ltr"}),
            "address": forms.TextInput(attrs={"class": "brut-input"}),
            "currency_unit": forms.Select(attrs={"class": "brut-input"}),
            "show_usd": forms.CheckboxInput(attrs={"class": "brut-check"}),
            "usd_rate": forms.NumberInput(attrs={"class": "brut-input", "step": "0.01", "min": "0", "dir": "ltr"}),
            "default_markup_percent": forms.NumberInput(
                attrs={"class": "brut-input", "step": "0.01", "min": "0", "dir": "ltr"}
            ),
            "low_stock_threshold": forms.NumberInput(attrs={"class": "brut-input", "min": "0", "dir": "ltr"}),
            "receipt_footer": forms.TextInput(attrs={"class": "brut-input"}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("show_usd") and not cleaned.get("usd_rate"):
            self.add_error("usd_rate", "برای نمایش دلاری، نرخ دلار را وارد کنید.")
        return cleaned
