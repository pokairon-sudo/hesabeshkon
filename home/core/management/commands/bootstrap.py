"""
ساخت اولیه‌ی سایت: مدیر، اپراتور و تنظیمات فروشگاه.

نمونه:
    python manage.py bootstrap --admin-email admin@shop.local --admin-password '***'
    python manage.py bootstrap --demo          # admin@shop.local / admin12345
"""

import secrets

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from accounts.models import ROLE_ADMIN, ROLE_OPERATOR, User
from core.models import ShopSettings


class Command(BaseCommand):
    help = "ساخت نقش‌ها، کاربر مدیر/اپراتور و تنظیمات پیش‌فرض"

    def add_arguments(self, parser):
        parser.add_argument("--admin-email", default="")
        parser.add_argument("--admin-password", default="")
        parser.add_argument("--admin-username", default="admin")
        parser.add_argument("--operator-email", default="")
        parser.add_argument("--operator-password", default="")
        parser.add_argument("--operator-username", default="operator")
        parser.add_argument("--demo", action="store_true", help="ساخت مدیر و اپراتور نمونه با رمز ساده")
        parser.add_argument("--reset", action="store_true", help="بازنویسی رمز کاربران موجود")

    def handle(self, *args, **options):
        for name in (ROLE_ADMIN, ROLE_OPERATOR):
            Group.objects.get_or_create(name=name)
        ShopSettings.load().save()

        if options["demo"]:
            admin_email = options["admin_email"] or "admin@shop.local"
            admin_password = options["admin_password"] or "admin12345"
            operator_email = options["operator_email"] or "operator@shop.local"
            operator_password = options["operator_password"] or "operator12345"
        else:
            admin_email = options["admin_email"]
            admin_password = options["admin_password"]
            operator_email = options["operator_email"]
            operator_password = options["operator_password"]

        if not admin_email:
            self.stdout.write(self.style.ERROR("--admin-email لازم است (یا از --demo استفاده کنید)."))
            return

        created = []
        admin = self._ensure_user(
            admin_email,
            options["admin_username"],
            admin_password,
            ROLE_ADMIN,
            reset=options["reset"],
            created=created,
        )
        self.stdout.write(self.style.SUCCESS(f"مدیر: {admin.email}"))

        if operator_email:
            operator = self._ensure_user(
                operator_email,
                options["operator_username"],
                operator_password,
                ROLE_OPERATOR,
                reset=options["reset"],
                created=created,
            )
            self.stdout.write(self.style.SUCCESS(f"اپراتور: {operator.email}"))

        if options["demo"]:
            self.stdout.write(self.style.WARNING("رمزهای نمونه را روی سرور واقعی عوض کنید!"))
            self.stdout.write("ورود مدیر: %s / %s" % (admin_email, admin_password))
            if operator_email:
                self.stdout.write("ورود اپراتور: %s / %s" % (operator_email, operator_password))

        if created:
            self.stdout.write("رمزهای ساخته‌شده:")
            for email, password in created:
                self.stdout.write(f"  {email} → {password}")

    def _ensure_user(self, email, username, password, role, *, reset, created):
        email = email.strip().lower()
        user = User.objects.filter(email=email).first()
        if user is None:
            password = password or secrets.token_urlsafe(9)
            user = User.objects.create_user(email=email, username=username, password=password)
            user.assign_role(role)
            created.append((email, password))
        else:
            if reset and password:
                user.set_password(password)
                user.save(update_fields=["password"])
            user.assign_role(role)
        return user
