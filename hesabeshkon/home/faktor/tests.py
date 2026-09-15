from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse

from faktor.models import FaktorSell, FaktorBuy, FaktorItem
from product.models import Product

User = get_user_model()


class FaktorItemModelTests(TestCase):
    """T4.1: FaktorItem.total_price with discount."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="u", email="u@example.com", password="pass12345"
        )
        self.product = Product.objects.create(
            name="Widget", serial_number="SN-1",
            price_for_company=Decimal("5.00"), price_for_customer=Decimal("10.00"),
        )
        self.sell = FaktorSell.objects.create(user=self.user)

    def test_total_price_with_no_discount(self):
        item = FaktorItem.objects.create(
            sell=self.sell, product=self.product, quantity=3,
            unit_price=Decimal("10.00"), user=self.user,
        )
        self.assertEqual(item.total_price, Decimal("30.00"))

    def test_total_price_with_discount(self):
        item = FaktorItem.objects.create(
            sell=self.sell, product=self.product, quantity=2,
            unit_price=Decimal("100.00"), discount_percent=Decimal("10.00"),
            user=self.user,
        )
        # 100 - 10% = 90 per unit, x2 = 180
        self.assertEqual(item.total_price, Decimal("180.0000"))

    def test_invoice_number_auto_generated(self):
        self.assertIsNotNone(self.sell.number)
        self.assertTrue(self.sell.number.startswith("S-"))
        self.assertIn(str(self.sell.date.year), self.sell.number)

    def test_buy_invoice_number_uses_b_prefix(self):
        buy = FaktorBuy.objects.create()
        self.assertTrue(buy.number.startswith("B-"))


class StaffUserMixin:
    """Shared setup: a 'personal' group staff user and a plain customer."""

    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff", email="staff@example.com", password="pass12345"
        )
        self.staff.groups.add(Group.objects.get(name="personal"))
        self.customer = User.objects.create_user(
            username="cust", email="cust@example.com", password="pass12345"
        )
        self.product = Product.objects.create(
            name="Widget", serial_number="SN-500", tag="kitchen",
            price_for_company=Decimal("5.00"), price_for_customer=Decimal("10.00"),
            count=5,
        )


class SellFlowTests(StaffUserMixin, TestCase):
    """
    T4.2: covers the sell invoice flow end-to-end under the new
    client-side-cart architecture — nothing touches the DB on GET, an
    empty cart is never saved, the whole invoice+items are created
    atomically in one POST, and success always returns to the same
    create page (never /edit/<pk>/).
    """

    def test_customer_is_blocked_from_faktor_entirely(self):
        self.client.login(email="cust@example.com", password="pass12345")
        resp = self.client.get(reverse("faktor:sell-list"))
        self.assertEqual(resp.status_code, 403)

    def test_opening_create_page_does_not_write_anything_to_the_db(self):
        self.client.login(email="staff@example.com", password="pass12345")
        resp = self.client.get(reverse("faktor:sell-create"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(FaktorSell.objects.count(), 0)

    def test_empty_cart_is_rejected_and_nothing_is_saved(self):
        self.client.login(email="staff@example.com", password="pass12345")
        resp = self.client.post(reverse("faktor:sell-create"), {
            "cart_json": "[]", "customer": "", "description": "",
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(FaktorSell.objects.count(), 0)

    def test_missing_cart_json_is_also_rejected(self):
        self.client.login(email="staff@example.com", password="pass12345")
        resp = self.client.post(reverse("faktor:sell-create"), {
            "customer": "Someone", "description": "",
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(FaktorSell.objects.count(), 0)

    def _post_cart(self, lines, customer="", description="", respond_json=False):
        import json
        payload = {
            "cart_json": json.dumps(lines),
            "customer": customer,
            "description": description,
        }
        if respond_json:
            payload["respond_json"] = "1"
        return self.client.post(reverse("faktor:sell-create"), payload)

    def test_saving_a_cart_creates_invoice_and_items_atomically(self):
        self.client.login(email="staff@example.com", password="pass12345")
        resp = self._post_cart([{"product_id": self.product.pk, "quantity": 2}], customer="Ali")

        # #3: always returns to the SAME create page, never /edit/<pk>/
        self.assertRedirects(resp, reverse("faktor:sell-create"))

        self.assertEqual(FaktorSell.objects.count(), 1)
        sell = FaktorSell.objects.first()
        self.assertEqual(sell.customer, "Ali")
        # #1: invoice number assigned automatically at the moment of save
        self.assertTrue(sell.number.startswith("S-"))

        item = FaktorItem.objects.get(sell=sell, product=self.product)
        self.assertEqual(item.quantity, 2)
        self.assertEqual(sell.total_price, self.product.price_for_customer * 2)

        self.product.refresh_from_db()
        self.assertEqual(self.product.count, 3)  # started at 5

    def test_requesting_more_than_available_stock_is_rejected(self):
        self.client.login(email="staff@example.com", password="pass12345")
        resp = self._post_cart([{"product_id": self.product.pk, "quantity": 999}])
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(FaktorSell.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.count, 5)  # untouched

    def test_unknown_product_id_is_rejected(self):
        self.client.login(email="staff@example.com", password="pass12345")
        resp = self._post_cart([{"product_id": 999999, "quantity": 1}])
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(FaktorSell.objects.count(), 0)

    def test_price_is_recomputed_server_side_not_trusted_from_client(self):
        # Security regression: only product_id/quantity are read from the
        # client cart — price always comes from the product's own current
        # price, so a tampered request can't under-charge.
        self.client.login(email="staff@example.com", password="pass12345")
        resp = self._post_cart([{
            "product_id": self.product.pk, "quantity": 1,
            "unit_price": "0.01",  # attempted tampering, should be ignored
        }])
        self.assertRedirects(resp, reverse("faktor:sell-create"))
        item = FaktorItem.objects.first()
        self.assertEqual(item.unit_price, self.product.final_price_for_customer())

    def test_print_flow_returns_json_and_still_saves_the_invoice(self):
        self.client.login(email="staff@example.com", password="pass12345")
        resp = self._post_cart(
            [{"product_id": self.product.pk, "quantity": 1}],
            customer="Zahra", respond_json=True,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["number"].startswith("S-"))
        self.assertEqual(data["customer"], "Zahra")
        self.assertEqual(len(data["items"]), 1)

        # the invoice was genuinely saved, not just previewed
        self.assertEqual(FaktorSell.objects.count(), 1)

    def test_editing_an_existing_invoice_redirects_to_the_list(self):
        # EditFaktorSellView is now only reached via "ویرایش" on an
        # already-saved invoice — separate from the create flow, and it
        # should return to the list, not back to a blank create screen.
        self.client.login(email="staff@example.com", password="pass12345")
        self._post_cart([{"product_id": self.product.pk, "quantity": 1}])
        sell = FaktorSell.objects.first()

        resp = self.client.post(
            reverse("faktor:sell-edit", kwargs={"pk": sell.pk}),
            {"customer": "Updated Name", "total_price": str(sell.total_price), "description": ""},
        )
        self.assertRedirects(resp, reverse("faktor:sell-list"))
        sell.refresh_from_db()
        self.assertEqual(sell.customer, "Updated Name")

    def test_edit_page_still_exposes_faktor_id_for_adding_more_items(self):
        # T1.1 regression, still relevant on the edit page.
        self.client.login(email="staff@example.com", password="pass12345")
        self._post_cart([{"product_id": self.product.pk, "quantity": 1}])
        sell = FaktorSell.objects.first()
        resp = self.client.get(reverse("faktor:sell-edit", kwargs={"pk": sell.pk}))
        self.assertContains(resp, f'data-faktor-id="{sell.pk}"')

    def test_add_item_on_edit_page_still_works_and_decrements_stock(self):
        self.client.login(email="staff@example.com", password="pass12345")
        self._post_cart([{"product_id": self.product.pk, "quantity": 1}])
        sell = FaktorSell.objects.first()
        self.product.refresh_from_db()
        stock_before = self.product.count

        other = Product.objects.create(
            name="Second Item", serial_number="SN-501",
            price_for_company=Decimal("2.00"), price_for_customer=Decimal("4.00"),
            count=10,
        )
        resp = self.client.post(reverse("faktor:add-item"), {
            "barcode": "SN-501", "faktor_id": sell.pk,
        })
        self.assertEqual(resp.json(), {"success": True})
        other.refresh_from_db()
        self.assertEqual(other.count, 9)

    def test_search_by_barcode_name_or_tag(self):
        self.client.login(email="staff@example.com", password="pass12345")
        for q in ["SN-500", "Widget", "kitchen"]:
            resp = self.client.get(reverse("faktor:search-products"), {"q": q})
            results = resp.json()["results"]
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["serial_number"], "SN-500")

    def test_sell_list_search_by_customer_and_number(self):
        self.client.login(email="staff@example.com", password="pass12345")
        self._post_cart([{"product_id": self.product.pk, "quantity": 1}], customer="Ali Rezai")
        sell = FaktorSell.objects.first()

        resp = self.client.get(reverse("faktor:sell-list"), {"q": "Ali"})
        self.assertContains(resp, "Ali Rezai")
        resp = self.client.get(reverse("faktor:sell-list"), {"q": sell.number})
        self.assertContains(resp, "Ali Rezai")
        resp = self.client.get(reverse("faktor:sell-list"), {"q": "NoSuchName"})
        self.assertNotContains(resp, "Ali Rezai")


@override_settings(FAKTOR_BUY_ENABLED=False)
class BuyDisabledTests(StaffUserMixin, TestCase):
    """#4: buy invoices are gated behind a settings flag."""

    def test_all_buy_urls_redirect_home_when_disabled(self):
        self.client.login(email="staff@example.com", password="pass12345")
        for url in [
            reverse("faktor:buy-create"),
            reverse("faktor:buy-list"),
        ]:
            resp = self.client.get(url)
            self.assertRedirects(resp, reverse("home"))

    def test_add_buy_item_blocked_when_disabled(self):
        self.client.login(email="staff@example.com", password="pass12345")
        resp = self.client.post(reverse("faktor:add-buy-item"), {
            "product_id": self.product.pk, "faktor_id": 1,
        })
        self.assertRedirects(resp, reverse("home"))


@override_settings(FAKTOR_BUY_ENABLED=True)
class BuyEnabledFlowTests(StaffUserMixin, TestCase):
    """T1.2/T1.4/T1.7: buy invoice flow when the feature IS turned on."""

    def test_buy_invoice_is_scoped_to_creating_user(self):
        self.client.login(email="staff@example.com", password="pass12345")
        resp = self.client.post(reverse("faktor:buy-create"), {
            "supplier": "", "total_price": "0", "description": "",
        })
        buy = FaktorBuy.objects.first()
        self.assertEqual(buy.user, self.staff)
        self.assertRedirects(resp, reverse("faktor:buy-edit", kwargs={"pk": buy.pk}))

    def test_add_buy_item_increments_stock(self):
        self.client.login(email="staff@example.com", password="pass12345")
        self.client.post(reverse("faktor:buy-create"), {
            "supplier": "", "total_price": "0", "description": "",
        })
        buy = FaktorBuy.objects.first()

        resp = self.client.post(reverse("faktor:add-buy-item"), {
            "product_id": self.product.pk, "faktor_id": buy.pk,
        })
        self.assertEqual(resp.json(), {"success": True})
        self.product.refresh_from_db()
        self.assertEqual(self.product.count, 6)

    def test_supplier_field_removed_from_form_ui(self):
        # #7: the field was removed from the template, but the model still
        # allows blank=True so the form itself keeps validating.
        self.client.login(email="staff@example.com", password="pass12345")
        resp = self.client.get(reverse("faktor:buy-create"))
        self.assertNotContains(resp, "تأمین‌کننده")
        self.assertNotContains(resp, 'id="supplier-input"')

    def test_another_users_buy_invoice_is_not_visible(self):
        other = User.objects.create_user(
            username="other_staff", email="other@example.com", password="pass12345"
        )
        other.groups.add(Group.objects.get(name="personal"))
        FaktorBuy.objects.create(user=other, supplier="Other Co")

        self.client.login(email="staff@example.com", password="pass12345")
        resp = self.client.get(reverse("faktor:buy-list"))
        self.assertNotContains(resp, "Other Co")
