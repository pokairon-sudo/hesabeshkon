"""
تنظیمات پروژه «حساب‌شکن» — نسخه ۲ (بروتالیست، مناسب VPS)

همه‌ی مقادیر حساس از متغیرهای محیطی خوانده می‌شوند. برای اجرای محلی
بدون هیچ متغیری هم کار می‌کند (DEBUG=True)، اما برای VPS حتماً
DJANGO_SECRET_KEY / DJANGO_DEBUG=0 / DJANGO_ALLOWED_HOSTS را تنظیم کنید.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# ---------------------------------------------------------------------------
# امنیت پایه
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    # فقط برای توسعه؛ روی VPS حتماً DJANGO_SECRET_KEY را ست کنید.
    "dev-only-insecure-key-change-me-on-server",
)
DEBUG = env_bool("DJANGO_DEBUG", True)

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1],testserver")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# اگر پشت Nginx/HTTPS هستید این‌ها خودکار فعال می‌شوند.
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"

# ---------------------------------------------------------------------------
# اپلیکیشن‌ها
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "core",
    "accounts",
    "homepage",
    "product",
    "faktor",
    "accounting",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    # فقط ادمین/اپراتور اجازه‌ی ورود به کل سایت را دارند.
    "accounts.middleware.AccessControlMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "home.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.shop_context",
            ],
        },
    },
]

WSGI_APPLICATION = "home.wsgi.application"

# ---------------------------------------------------------------------------
# دیتابیس‌ها
#   default     : داده‌های عملیاتی فروشگاه
#   accountant  : دیتابیس جداگانه‌ی حسابدار (فقط فاکتورهای نهایی‌شده)
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("DJANGO_DB_PATH", str(BASE_DIR / "db.sqlite3")),
        "OPTIONS": {"timeout": 20},
    },
    "accountant": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get(
            "ACCOUNTANT_DB_PATH", str(BASE_DIR / "accountant.sqlite3")
        ),
        "OPTIONS": {"timeout": 20},
    },
}

DATABASE_ROUTERS = ["accounting.router.AccountantRouter"]

# ---------------------------------------------------------------------------
# احراز هویت
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# بین‌المللی‌سازی — فارسی و ساعت تهران
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "fa-ir"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# فایل‌های استاتیک و آپلود
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

FILE_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 15 * 1024 * 1024

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# ایمیل (برای بازنشانی رمز در محیط توسعه در ترمینال چاپ می‌شود)
# ---------------------------------------------------------------------------
EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = os.environ.get("DJANGO_DEFAULT_FROM_EMAIL", "hesabeshkon@localhost")

# ---------------------------------------------------------------------------
# تنظیمات اختصاصی برنامه
# ---------------------------------------------------------------------------
# اگر روزی خواستید فاکتور خرید را موقتاً ببندید، این را False کنید.
FAKTOR_BUY_ENABLED = env_bool("FAKTOR_BUY_ENABLED", True)

# حداکثر تعداد ردیف در یک فاکتور (جلوگیری از سوءاستفاده)
MAX_INVOICE_LINES = 200
MAX_LINE_QUANTITY = 100_000

# ---------------------------------------------------------------------------
# خواندن فاکتور با مدل بینایی (اختیاری، سازگار با OpenAI)
# ---------------------------------------------------------------------------
# اگر OCR_VISION_API_KEY و OCR_VISION_MODEL ست شده باشند، عکس فاکتور اول به
# مدل بینایی داده می‌شود؛ در صورت خطا/نبود کلید، Tesseract استفاده می‌شود.
# مثال برای OpenRouter:  https://openrouter.ai/api/v1
# مثال برای Ollama محلی: http://127.0.0.1:11434/v1  (کلید را "ollama" بگذارید)
OCR_VISION_BASE_URL = os.environ.get("OCR_VISION_BASE_URL", "https://api.openai.com/v1")
OCR_VISION_API_KEY = os.environ.get("OCR_VISION_API_KEY", "")
OCR_VISION_MODEL = os.environ.get("OCR_VISION_MODEL", "")
OCR_VISION_TIMEOUT = int(os.environ.get("OCR_VISION_TIMEOUT", "90"))


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "faktor": {"handlers": ["console"], "level": "INFO"},
        "accounting": {"handlers": ["console"], "level": "INFO"},
    },
}
