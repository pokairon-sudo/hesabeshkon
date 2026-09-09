from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from .models import Product

User = get_user_model()


class ProductModelTests(TestCase):
    """T4.1: covers Product.final_price_for_customer() for both offer types."""

    def test_percent_offer_discounts_correctly(self):
        p = Product.objects.create(
            name="Widget", serial_number="SN-1",
            price_for_company=Decimal("10.00"), price_for_customer=Decimal("100.00"),
            offer_type="percent", offer_value=Decimal("10.00"),
        )
        self.assertEqual(p.final_price_for_customer(), Decimal("90.00"))

    def test_fixed_price_offer_discounts_correctly(self):
        p = Product.objects.create(
            name="Gadget", serial_number="SN-2",
            price_for_company=Decimal("10.00"), price_for_customer=Decimal("100.00"),
            offer_type="price", offer_value=Decimal("15.00"),
        )
        self.assertEqual(p.final_price_for_customer(), Decimal("85.00"))

    def test_offer_cannot_push_price_below_zero(self):
        p = Product.objects.create(
            name="Cheap", serial_number="SN-3",
            price_for_company=Decimal("1.00"), price_for_customer=Decimal("5.00"),
            offer_type="price", offer_value=Decimal("999.00"),
        )
        self.assertEqual(p.final_price_for_customer(), Decimal("0"))

    def test_zero_offer_returns_full_price(self):
        p = Product.objects.create(
            name="Full Price", serial_number="SN-4",
            price_for_company=Decimal("10.00"), price_for_customer=Decimal("50.00"),
        )
        self.assertEqual(p.final_price_for_customer(), Decimal("50.00"))


class ProductViewPermissionTests(TestCase):
    """
    T4.2/T2.1/T2.2: any logged-in user can browse the product list, but
    only 'personal'/'admin' group members (or staff) can create/edit/delete.
    """

    def setUp(self):
        self.customer = User.objects.create_user(
            username="cust", email="cust@example.com", password="pass12345"
        )
        self.staff = User.objects.create_user(
            username="staff", email="staff@example.com", password="pass12345"
        )
        self.staff.groups.add(Group.objects.get(name="personal"))
        self.product = Product.objects.create(
            name="Widget", serial_number="SN-100",
            price_for_company=Decimal("5.00"), price_for_customer=Decimal("10.00"),
        )

    def test_anonymous_is_redirected_to_login(self):
        resp = self.client.get(reverse("product:l-product"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp.url)

    def test_customer_can_view_list(self):
        self.client.login(email="cust@example.com", password="pass12345")
        resp = self.client.get(reverse("product:l-product"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Widget")

    def test_customer_cannot_create_product(self):
        self.client.login(email="cust@example.com", password="pass12345")
        resp = self.client.get(reverse("product:c-product"))
        self.assertEqual(resp.status_code, 403)

        resp = self.client.post(reverse("product:c-product"), {
            "name": "Sneaky", "tag": "", "serial_number": "HACK-1",
            "price_for_company": "1", "price_for_customer": "2",
            "count": "1", "offer_value": "0", "offer_type": "percent",
        })
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(Product.objects.filter(serial_number="HACK-1").exists())

    def test_customer_cannot_edit_or_delete_product(self):
        self.client.login(email="cust@example.com", password="pass12345")
        resp = self.client.get(reverse("product:e-product", kwargs={"pk": self.product.pk}))
        self.assertEqual(resp.status_code, 403)
        resp = self.client.post(reverse("product:d-product", kwargs={"pk": self.product.pk}))
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_staff_can_create_edit_delete_product(self):
        self.client.login(email="staff@example.com", password="pass12345")

        resp = self.client.post(reverse("product:c-product"), {
            "name": "Real Product", "tag": "", "serial_number": "REAL-1",
            "price_for_company": "1", "price_for_customer": "2",
            "count": "5", "offer_value": "0", "offer_type": "percent",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Product.objects.filter(serial_number="REAL-1").exists())

        resp = self.client.post(
            reverse("product:e-product", kwargs={"pk": self.product.pk}),
            {
                "name": "Widget Renamed", "tag": "", "serial_number": "SN-100",
                "price_for_company": "5", "price_for_customer": "12",
                "count": "0", "offer_value": "0", "offer_type": "percent",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Widget Renamed")

        resp = self.client.post(reverse("product:d-product", kwargs={"pk": self.product.pk}))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())

    def test_search_by_name_and_serial(self):
        self.client.login(email="cust@example.com", password="pass12345")
        resp = self.client.get(reverse("product:l-product"), {"q": "Widget", "field": "name"})
        self.assertContains(resp, "Widget")
        resp = self.client.get(reverse("product:l-product"), {"q": "SN-100", "field": "serial"})
        self.assertContains(resp, "Widget")
        resp = self.client.get(reverse("product:l-product"), {"q": "nomatch", "field": "name"})
        self.assertNotContains(resp, "Widget")
