from decimal import Decimal

from django import forms

from .models import Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "tag",
            "serial_number",
            "unit",
            "price_for_company",
            "price_for_customer",
            "count",
            "offer_value",
            "offer_type",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "brut-input", "placeholder": "مثلاً قهوه اسپرسو"}),
            "tag": forms.TextInput(attrs={"class": "brut-input", "placeholder": "مثلاً نوشیدنی"}),
            "serial_number": forms.TextInput(
                attrs={"class": "brut-input", "dir": "ltr", "placeholder": "خالی = ساخت خودکار بارکد"}
            ),
            "unit": forms.Select(attrs={"class": "brut-input"}),
            "price_for_company": forms.NumberInput(
                attrs={"class": "brut-input", "step": "0.01", "min": "0", "dir": "ltr", "data-money": "1"}
            ),
            "price_for_customer": forms.NumberInput(
                attrs={"class": "brut-input", "step": "0.01", "min": "0", "dir": "ltr", "data-money": "1"}
            ),
            "count": forms.NumberInput(attrs={"class": "brut-input", "min": "0", "dir": "ltr"}),
            "offer_value": forms.NumberInput(
                attrs={"class": "brut-input", "step": "0.01", "min": "0", "dir": "ltr"}
            ),
            "offer_type": forms.Select(attrs={"class": "brut-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "brut-check"}),
        }
        labels = {
            "serial_number": "بارکد",
            "price_for_company": "قیمت خرید (تومان)",
            "price_for_customer": "قیمت فروش (تومان)",
            "offer_value": "مقدار تخفیف",
            "offer_type": "نوع تخفیف",
        }
        help_texts = {
            "serial_number": "می‌توانید بارکد را اسکن کنید یا خالی بگذارید تا خودکار ساخته شود.",
            "offer_value": "برای تخفیف درصدی عدد ۰ تا ۱۰۰ و برای تخفیف ثابت، مبلغ به تومان.",
        }

    def clean_serial_number(self):
        value = (self.cleaned_data.get("serial_number") or "").strip()
        if value:
            qs = Product.objects.filter(serial_number=value)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("این بارکد قبلاً برای کالای دیگری ثبت شده است.")
        return value

    def clean(self):
        cleaned = super().clean()
        offer_type = cleaned.get("offer_type")
        offer_value = cleaned.get("offer_value") or Decimal("0")
        if offer_type == "percent" and offer_value > 100:
            self.add_error("offer_value", "تخفیف درصدی نمی‌تواند بیشتر از ۱۰۰ باشد.")
        if cleaned.get("price_for_customer") is not None and cleaned.get("price_for_company") is not None:
            if cleaned["price_for_customer"] < 0 or cleaned["price_for_company"] < 0:
                self.add_error("price_for_customer", "قیمت نمی‌تواند منفی باشد.")
        return cleaned
