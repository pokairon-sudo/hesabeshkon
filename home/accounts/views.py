from django.contrib import messages
from django.contrib.auth import login, logout
from django.core.cache import cache
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView

from .forms import EmailAuthenticationForm, ManagedUserForm, ProfileForm
from .middleware import safe_next_url
from .mixins import AdminRequiredMixin
from .models import User


def _client_ip(request) -> str:
    # Nginx این هدر را ست می‌کند؛ برای اجرای مستقیم، REMOTE_ADDR کافی است.
    return (
        request.META.get("HTTP_X_REAL_IP")
        or request.META.get("REMOTE_ADDR")
        or "unknown"
    )


class LoginView(View):
    template_name = "login.html"
    form_class = EmailAuthenticationForm

    def get(self, request):
        if request.user.is_authenticated and request.user.has_app_access:
            return redirect("home")
        return render(request, self.template_name, {"form": self.form_class()})

    def post(self, request):
        ip = _client_ip(request)
        cache_key = f"login-fail:{ip}"
        failures = cache.get(cache_key, 0)
        if failures >= 10:
            form = self.form_class(request, data=request.POST)
            form.add_error(None, "تلاش‌های ناموفق زیاد بوده است؛ ۵ دقیقه بعد دوباره تلاش کنید.")
            return render(request, self.template_name, {"form": form}, status=429)

        form = self.form_class(request, data=request.POST)
        if not form.is_valid():
            cache.set(cache_key, failures + 1, 300)
            return render(request, self.template_name, {"form": form}, status=400)

        user = form.get_user()
        if not user.has_app_access:
            cache.set(cache_key, failures + 1, 300)
            messages.error(request, "حساب شما نقش مدیر یا اپراتور ندارد. با مدیر تماس بگیرید.")
            return render(request, self.template_name, {"form": self.form_class()}, status=403)

        cache.delete(cache_key)
        if not user.has_app_access:
            # کاربر بدون نقش (مثلاً ساخته‌شده در پنل جنگو بدون گروه)
            messages.error(request, "حساب شما نقش مدیر یا اپراتور ندارد. با مدیر تماس بگیرید.")
            return render(request, self.template_name, {"form": self.form_class()}, status=403)

        login(request, user)
        messages.success(request, f"خوش آمدید، {user.username}.")
        return redirect(safe_next_url(request, "home"))


class LogoutView(View):
    """خروج فقط با POST (جلوگیری از خروج با لینک/CSRF)."""

    def post(self, request):
        logout(request)
        messages.success(request, "از حساب خارج شدید.")
        return redirect("login")

    def get(self, request):
        return redirect("home")


class ProfileView(LoginRequiredMixin, View):
    template_name = "profile.html"

    def get(self, request):
        return render(request, self.template_name, {"form": ProfileForm(instance=request.user)})

    def post(self, request):
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "پروفایل به‌روزرسانی شد.")
            return redirect("profile")
        return render(request, self.template_name, {"form": form}, status=400)


class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = "registration/password_change_form.html"
    success_url = reverse_lazy("password_change_done")


class UserListView(AdminRequiredMixin, ListView):
    model = User
    template_name = "accounts/user_list.html"
    context_object_name = "users"
    paginate_by = 30

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(username__icontains=q) | qs.filter(email__icontains=q)
        return qs


class UserCreateView(AdminRequiredMixin, View):
    template_name = "accounts/user_form.html"

    def get(self, request):
        return render(request, self.template_name, {"form": ManagedUserForm(), "is_new": True})

    def post(self, request):
        form = ManagedUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"کاربر «{user.username}» ساخته شد.")
            return redirect("user-list")
        return render(request, self.template_name, {"form": form, "is_new": True}, status=400)


class UserUpdateView(AdminRequiredMixin, View):
    template_name = "accounts/user_form.html"

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        return render(
            request, self.template_name, {"form": ManagedUserForm(instance=user), "is_new": False, "obj": user}
        )

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        form = ManagedUserForm(request.POST, instance=user)
        if form.is_valid():
            if user == request.user and (
                form.cleaned_data.get("role") != "admin" or not form.cleaned_data.get("is_active")
            ):
                messages.error(request, "نمی‌توانید نقش یا فعال‌بودن حساب خودتان را حذف کنید.")
                return render(
                    request,
                    self.template_name,
                    {"form": form, "is_new": False, "obj": user},
                    status=400,
                )
            user = form.save()
            messages.success(request, f"کاربر «{user.username}» ذخیره شد.")
            return redirect("user-list")
        return render(
            request, self.template_name, {"form": form, "is_new": False, "obj": user}, status=400
        )
