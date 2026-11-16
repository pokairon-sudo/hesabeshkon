from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import ROLE_ADMIN, ROLE_OPERATOR

from .models import ShopSettings, format_money
from .templatetags.jalali import gregorian_to_jalali

User = get_user_model()


class MoneyTests(TestCase):
    def setUp(self):
        self.shop = ShopSettings.load()
        self.shop.currency_unit = ShopSettings.CURRENCY_TOMAN
        self.shop.show_usd = False
        self.shop.usd_rate = Decimal("0")
        self.shop.save()

    def test_toman_format(self):
        self.assertEqual(format_money(Decimal("1234567")), "1,234,567 تومان")

    def test_rial_multiplies_by_ten(self):
        self.shop.currency_unit = ShopSettings.CURRENCY_RIAL
        self.shop.save()
        self.assertEqual(format_money(Decimal("1234")), "12,340 ریال")

    def test_usd_suffix(self):
        self.shop.show_usd = True
        self.shop.usd_rate = Decimal("100000")
        self.shop.save()
        self.assertIn("$10.00", format_money(Decimal("1000000"), with_usd=True))
        self.assertNotIn("$", format_money(Decimal("1000000")))

    def test_decimal_precision(self):
        self.assertIn("1,234.56", format_money(Decimal("1234.56")))


class JalaliTests(TestCase):
    def test_known_dates(self):
        self.assertEqual(gregorian_to_jalali(2026, 3, 21), (1405, 1, 1))
        self.assertEqual(gregorian_to_jalali(2024, 1, 1), (1402, 10, 11))
        self.assertEqual(gregorian_to_jalali(2025, 3, 20), (1403, 12, 30))


class SettingsTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@c.local", username="admin", password="pass12345"
        )
        self.admin.assign_role(ROLE_ADMIN)
        self.operator = User.objects.create_user(
            email="op@c.local", username="op", password="pass12345"
        )
        self.operator.assign_role(ROLE_OPERATOR)

    def test_operator_cannot_access_settings(self):
        self.client.login(email="op@c.local", password="pass12345")
        response = self.client.get(reverse("settings"))
        self.assertRedirects(response, reverse("home"))

    def test_admin_can_change_currency_and_usd_rate(self):
        self.client.login(email="admin@c.local", password="pass12345")
        response = self.client.post(
            reverse("settings"),
            {
                "shop_name": "کافه من",
                "phone": "02112345678",
                "address": "تهران",
                "currency_unit": ShopSettings.CURRENCY_RIAL,
                "show_usd": "on",
                "usd_rate": "90000",
                "default_markup_percent": "25",
                "low_stock_threshold": "3",
                "receipt_footer": "ممنون",
            },
        )
        self.assertRedirects(response, reverse("settings"))
        shop = ShopSettings.load()
        self.assertEqual(shop.shop_name, "کافه من")
        self.assertEqual(shop.currency_unit, ShopSettings.CURRENCY_RIAL)
        self.assertTrue(shop.show_usd)
        self.assertEqual(shop.usd_rate, Decimal("90000"))

    def test_show_usd_requires_rate(self):
        self.client.login(email="admin@c.local", password="pass12345")
        response = self.client.post(
            reverse("settings"),
            {
                "shop_name": "کافه",
                "currency_unit": ShopSettings.CURRENCY_TOMAN,
                "show_usd": "on",
                "usd_rate": "0",
                "default_markup_percent": "20",
                "low_stock_threshold": "5",
                "receipt_footer": "",
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_singleton_is_pk_one(self):
        shop = ShopSettings.load()
        self.assertEqual(shop.pk, 1)
        ShopSettings(shop_name="other").save()
        self.assertEqual(ShopSettings.objects.count(), 1)
