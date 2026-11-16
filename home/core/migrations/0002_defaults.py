from django.db import migrations


def create_settings(apps, schema_editor):
    ShopSettings = apps.get_model("core", "ShopSettings")
    ShopSettings.objects.get_or_create(
        pk=1,
        defaults={
            "shop_name": "حساب‌شکن",
            "receipt_footer": "از خرید شما سپاسگزاریم 🌿",
        },
    )


def remove_settings(apps, schema_editor):
    ShopSettings = apps.get_model("core", "ShopSettings")
    ShopSettings.objects.filter(pk=1).delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]
    operations = [migrations.RunPython(create_settings, remove_settings)]
