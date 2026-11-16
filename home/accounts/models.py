import re

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    Group,
    PermissionsMixin,
)
from django.core.validators import RegexValidator
from django.db import models

ROLE_ADMIN = "admin"
ROLE_OPERATOR = "operator"
ROLE_CHOICES = [(ROLE_ADMIN, "مدیر"), (ROLE_OPERATOR, "اپراتور")]


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _unique_username(self, email: str, username: str | None) -> str:
        base = (username or email.split("@")[0] or "user").strip()
        base = re.sub(r"[^\w.@+-]", "", base)[:140] or "user"
        candidate = base
        counter = 1
        while self.model._default_manager.filter(username=candidate).exists():
            counter += 1
            candidate = f"{base}{counter}"
        return candidate

    def create_user(self, email, password=None, username=None, **extra_fields):
        if not email:
            raise ValueError("ایمیل الزامی است.")
        email = self.normalize_email(email).lower()
        username = self._unique_username(email, username)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, username=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("سوپریوزر باید is_staff=True باشد.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("سوپریوزر باید is_superuser=True باشد.")
        return self.create_user(email, password, username, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    کاربران این برنامه فقط دو نقش دارند: مدیر و اپراتور.
    مشتری هیچ حساب کاربری‌ای ندارد و به سایت دسترسی ندارد.
    """

    phone_regex = RegexValidator(
        regex=r"^\+?[0-9]{7,15}$",
        message="شماره تلفن باید فقط رقم (و اختیاراً +) باشد؛ بین ۷ تا ۱۵ رقم.",
    )

    username = models.CharField("نام کاربری", max_length=150, unique=True)
    email = models.EmailField("ایمیل", unique=True)
    phone = models.CharField(
        "تلفن", validators=[phone_regex], max_length=16, blank=True, default=""
    )

    is_active = models.BooleanField("فعال", default=True)
    is_staff = models.BooleanField("دسترسی به پنل جنگو", default=False)

    date_joined = models.DateTimeField("تاریخ عضویت", auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"
        ordering = ["username"]

    def __str__(self):
        return f"{self.username} <{self.email}>"

    # ------------------------------------------------------------------
    # نقش‌ها
    # ------------------------------------------------------------------
    @property
    def role(self) -> str | None:
        if self.is_superuser or self.is_staff:
            return ROLE_ADMIN
        if self.groups.filter(name=ROLE_ADMIN).exists():
            return ROLE_ADMIN
        if self.groups.filter(name=ROLE_OPERATOR).exists():
            return ROLE_OPERATOR
        return None

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN

    @property
    def is_operator(self) -> bool:
        return self.role == ROLE_OPERATOR

    @property
    def has_app_access(self) -> bool:
        return self.role in (ROLE_ADMIN, ROLE_OPERATOR)

    # سازگاری با کدهای قدیمی قالب‌ها
    @property
    def is_staff_or_manager(self) -> bool:
        return self.has_app_access

    def get_role_display(self) -> str:
        return dict(ROLE_CHOICES).get(self.role, "بدون دسترسی")

    def assign_role(self, role: str) -> None:
        """نقش را تنظیم می‌کند؛ سوپریوزر همیشه مدیر می‌ماند."""
        admin_group, _ = Group.objects.get_or_create(name=ROLE_ADMIN)
        operator_group, _ = Group.objects.get_or_create(name=ROLE_OPERATOR)
        if self.is_superuser:
            self.is_staff = True
            self.groups.add(admin_group)
            self.save(update_fields=["is_staff"])
            return
        self.groups.remove(admin_group, operator_group)
        if role == ROLE_ADMIN:
            self.groups.add(admin_group)
            self.is_staff = True
        elif role == ROLE_OPERATOR:
            self.groups.add(operator_group)
            self.is_staff = False
        else:
            self.is_staff = False
        self.save(update_fields=["is_staff"])
