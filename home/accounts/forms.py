from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import ROLE_CHOICES, ROLE_OPERATOR, User


class EmailAuthenticationForm(AuthenticationForm):
    """ورود با ایمیل؛ برچسب فیلد هم «ایمیل» است."""

    username = forms.EmailField(
        label="ایمیل",
        widget=forms.EmailInput(
            attrs={
                "autofocus": True,
                "autocomplete": "username",
                "placeholder": "you@example.com",
                "class": "brut-input",
            }
        ),
    )
    def clean_username(self):
        return (self.cleaned_data.get("username") or "").strip().lower()

    password = forms.CharField(
        label="رمز عبور",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
                "placeholder": "••••••••",
                "class": "brut-input",
            }
        ),
    )


class ProfileForm(forms.ModelForm):
    def clean_email(self):
        return (self.cleaned_data.get("email") or "").strip().lower()

    class Meta:
        model = User
        fields = ["username", "email", "phone"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "brut-input"}),
            "email": forms.EmailInput(attrs={"class": "brut-input"}),
            "phone": forms.TextInput(attrs={"class": "brut-input", "dir": "ltr"}),
        }


class ManagedUserForm(forms.ModelForm):
    """فرم مدیر برای ساخت/ویرایش اپراتور و مدیر."""

    role = forms.ChoiceField(
        label="نقش",
        choices=ROLE_CHOICES,
        initial=ROLE_OPERATOR,
        widget=forms.Select(attrs={"class": "brut-input"}),
    )
    password1 = forms.CharField(
        label="رمز عبور",
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "brut-input", "autocomplete": "new-password"}),
        help_text="برای کاربر جدید الزامی است. برای ویرایش، خالی بگذارید تا تغییر نکند.",
    )
    password2 = forms.CharField(
        label="تکرار رمز عبور",
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "brut-input", "autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = ["username", "email", "phone", "is_active"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "brut-input"}),
            "email": forms.EmailInput(attrs={"class": "brut-input"}),
            "phone": forms.TextInput(attrs={"class": "brut-input", "dir": "ltr"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["role"].initial = self.instance.role or ROLE_OPERATOR
            self.fields["password1"].required = False
            if self.instance.is_superuser:
                self.fields["role"].disabled = True
                self.fields["role"].initial = "admin"
        else:
            self.fields["password1"].required = True

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").lower()
        qs = User.objects.filter(email=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("این ایمیل قبلاً ثبت شده است.")
        return email

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        qs = User.objects.filter(username=username)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("این نام کاربری قبلاً ثبت شده است.")
        return username

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 or p2:
            if p1 != p2:
                self.add_error("password2", "رمز عبور و تکرار آن یکسان نیستند.")
            elif len(p1) < 8:
                self.add_error("password1", "رمز عبور باید حداقل ۸ کاراکتر باشد.")
        elif not self.instance.pk:
            self.add_error("password1", "برای کاربر جدید رمز عبور الزامی است.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        if not user.pk:
            user.set_password(self.cleaned_data["password1"])
        elif self.cleaned_data.get("password1"):
            user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            user.assign_role(self.cleaned_data["role"])
        return user


class UserRegisterForm(UserCreationForm):
    """اگر روزی ثبت‌نام داخلی لازم شد (فعلاً استفاده نمی‌شود)."""

    class Meta:
        model = User
        fields = ["username", "email", "phone"]
