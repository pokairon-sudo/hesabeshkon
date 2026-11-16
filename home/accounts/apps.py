from django.apps import AppConfig
from django.db.models.signals import post_migrate


def grant_admin_group_permissions(sender, using, **kwargs):
    """به گروه «مدیر» همه‌ی مجوزهای پنل جنگو را می‌دهد (فقط دیتابیس اصلی)."""
    if using != "default":
        return
    from django.contrib.auth.models import Group, Permission

    admin_group, _ = Group.objects.using(using).get_or_create(name="admin")
    admin_group.permissions.set(Permission.objects.using(using).all())


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "کاربران و نقش‌ها"

    def ready(self):
        post_migrate.connect(
            grant_admin_group_permissions,
            sender=self,
            dispatch_uid="accounts.grant_admin_group_permissions",
        )
