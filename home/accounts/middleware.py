from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from urllib.parse import urlencode


class AccessControlMiddleware:
    """
    دروازه‌ی سراسری ورود.

    - هر صفحه‌ای (به‌جز ورود، استاتیک و پنل جنگو) فقط برای کاربر واردشده باز است.
    - کاربری که نقش «مدیر» یا «اپراتور» ندارد، بلافاصله از حساب خارج می‌شود.
    - پنل جنگو مسیر خودش را دارد و فقط is_staff (=مدیر) به آن راه دارد.
    """

    PUBLIC_PREFIXES = (
        settings.STATIC_URL,
        settings.MEDIA_URL,
        "/favicon.ico",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def _is_public(self, path: str) -> bool:
        if path == settings.LOGIN_URL or path == reverse("login"):
            return True
        return any(path.startswith(prefix) for prefix in self.PUBLIC_PREFIXES)

    def __call__(self, request):
        path = request.path_info
        user = getattr(request, "user", None)

        if not self._is_public(path):
            if user is None or not user.is_authenticated:
                login_url = reverse("login")
                if path != login_url:
                    return redirect(f"{login_url}?{urlencode({'next': request.get_full_path()})}")
            elif not user.has_app_access:
                logout(request)
                messages.error(request, "حساب شما نقش مدیر یا اپراتور ندارد.")
                return redirect("login")
            elif not user.is_active:
                logout(request)
                messages.error(request, "حساب شما غیرفعال شده است.")
                return redirect("login")
            elif path.startswith("/admin/") and not user.is_staff:
                messages.error(request, "پنل جنگو فقط برای مدیر است.")
                return redirect("home")

        response = self.get_response(request)
        return response


def safe_next_url(request, fallback="home"):
    """جلوگیری از Open Redirect در پارامتر next."""
    candidate = request.POST.get("next") or request.GET.get("next")
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return reverse(fallback)
