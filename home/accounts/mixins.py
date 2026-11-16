from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages


class AppAccessRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """اجازه‌ی ورود به بخش‌های داخلی: مدیر یا اپراتور."""

    def test_func(self):
        user = self.request.user
        return bool(user.is_authenticated and user.has_app_access)


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """فقط مدیر: گزارش‌ها، تنظیمات، مدیریت کاربران، حذف محصول."""

    def test_func(self):
        return bool(self.request.user.is_authenticated and self.request.user.is_admin)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "این بخش فقط برای مدیر مجاز است.")
            return redirect("home")
        return super().handle_no_permission()


class OperatorOrAdminRequiredMixin(AppAccessRequiredMixin):
    """نام صریح برای خوانایی؛ همان دسترسی مدیر/اپراتور."""


class StaffGroupRequiredMixin(AppAccessRequiredMixin):
    """نام قدیمی، برای سازگاری با کدهای قبلی."""


class AdminOrOwnerMixin:
    """
    کمکی برای فاکتورها:
    مدیر همه‌ی فاکتورها را می‌بیند، اپراتور فقط فاکتورهای خودش را.
    """

    owner_field = "user"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_admin:
            return qs
        return qs.filter(**{self.owner_field: user})


def deny(request, message="دسترسی ندارید."):
    messages.error(request, message)
    raise PermissionDenied(message)
