from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import ROLE_ADMIN, ROLE_OPERATOR

from .models import Product

User = get_user_model()


class ProductModelTests(TestCase):
    def test_percent_offer(self):
        p = Product(
            name="A",
            serial_number="SN-1",
            price_for_company=Decimal("10"),
            price_for_customer=Decimal("100"),
            offer_type="percent",
            offer_value=Decimal("10"),
        )
        self.assertEqual(p.final_price_for_customer(), Decimal("90.00"))
        self.assertEqual(p.profit_per_unit, Decimal("80.00"))
        self.assertEqual(p.margin_percent, Decimal("800.0"))

    def test_fixed_offer_and_clamp(self):
        p = Product(
            name="B",
            serial_number="SN-2",
            price_for_customer=Decimal("5"),
            offer_type="price",
            offer_value=Decimal("999"),
        )
        self.assertEqual(p.final_price_for_customer(), Decimal("0.00"))

    def test_auto_barcode_generated_and_unique(self):
        first = Product.objects.create(name="No barcode", price_for_customer=Decimal("1"))
        second = Product.objects.create(name="No barcode 2", price_for_customer=Decimal("1"))
        self.assertTrue(first.serial_number)
        self.assertTrue(second.serial_number)
        self.assertNotEqual(first.serial_number, second.serial_number)
        self.assertEqual(len(first.serial_number), 13)
        self.assertTrue(first.serial_number.isdigit())

    def test_negative_price_rejected_by_form(self):
        admin = User.objects.create_user(email="a@t.local", username="a", password="x")
        admin.assign_role(ROLE_ADMIN)
        self.client.force_login(admin)
        response = self.client.post(
            reverse("product:c-product"),
            {
                "name": "Bad",
                "tag": "",
                "serial_number": "",
                "unit": "piece",
                "price_for_company": "-1",
                "price_for_customer": "10",
                "count": "0",
                "offer_value": "0",
                "offer_type": "percent",
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Product.objects.filter(name="Bad").exists())


class ProductViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@t.local", username="admin", password="pass12345"
        )
        self.admin.assign_role(ROLE_ADMIN)
        self.operator = User.objects.create_user(
            email="op@t.local", username="op", password="pass12345"
        )
        self.operator.assign_role(ROLE_OPERATOR)
        self.product = Product.objects.create(
            name="قهوه",
            tag="نوشیدنی",
            serial_number="1111111111111",
            price_for_company=Decimal("100"),
            price_for_customer=Decimal("200"),
            count=10,
        )

    def test_operator_can_create_product_json(self):
        self.client.login(email="op@t.local", password="pass12345")
        response = self.client.post(
            reverse("product:c-product"),
            {
                "name": "لاته",
                "tag": "نوشیدنی",
                "serial_number": "",
                "unit": "piece",
                "price_for_company": "50",
                "price_for_customer": "90",
                "count": "5",
                "offer_value": "0",
                "offer_type": "percent",
                "is_active": "on",
                "respond_json": "1",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["product"]["name"], "لاته")
        self.assertTrue(data["product"]["serial_number"])

    def test_operator_cannot_delete(self):
        self.client.login(email="op@t.local", password="pass12345")
        response = self.client.post(reverse("product:d-product", args=[self.product.pk]))
        self.assertRedirects(response, reverse("home"))
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_admin_can_delete(self):
        self.client.login(email="admin@t.local", password="pass12345")
        response = self.client.post(reverse("product:d-product", args=[self.product.pk]))
        self.assertRedirects(response, reverse("product:l-product"))
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())

    def test_search_by_name_and_barcode(self):
        self.client.login(email="op@t.local", password="pass12345")
        response = self.client.get(reverse("product:l-product"), {"q": "قهوه"})
        self.assertContains(response, "قهوه")
        response = self.client.get(
            reverse("product:l-product"), {"q": "1111111", "field": "barcode"}
        )
        self.assertContains(response, "قهوه")
        response = self.client.get(reverse("product:l-product"), {"q": "ناموجود"})
        self.assertNotContains(response, "قهوه")

    def test_low_stock_filter(self):
        self.product.count = 0
        self.product.save()
        self.client.login(email="op@t.local", password="pass12345")
        response = self.client.get(reverse("product:l-product"), {"low": "1"})
        self.assertContains(response, "قهوه")

    def test_edit_product(self):
        self.client.login(email="op@t.local", password="pass12345")
        response = self.client.post(
            reverse("product:e-product", args=[self.product.pk]),
            {
                "name": "قهوه ویژه",
                "tag": "نوشیدنی",
                "serial_number": "1111111111111",
                "unit": "piece",
                "price_for_company": "100",
                "price_for_customer": "250",
                "count": "8",
                "offer_value": "0",
                "offer_type": "percent",
                "is_active": "on",
                "respond_json": "1",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "قهوه ویژه")
        self.assertEqual(self.product.price_for_customer, Decimal("250"))

    def test_json_detail(self):
        self.client.login(email="op@t.local", password="pass12345")
        response = self.client.get(reverse("product:detail", args=[self.product.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["product"]["id"], self.product.pk)
