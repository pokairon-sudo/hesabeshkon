import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounting.models import AccountantInvoice
from accounts.models import ROLE_ADMIN, ROLE_OPERATOR
from product.models import Product

from .models import FaktorBuy, FaktorItem, FaktorSell, InvoiceStatus
from .ocr import parse_invoice_text

User = get_user_model()


class FaktorTestBase(TestCase):
    databases = {"default", "accountant"}

    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@f.local", username="admin", password="pass12345"
        )
        self.admin.assign_role(ROLE_ADMIN)
        self.operator = User.objects.create_user(
            email="op@f.local", username="op", password="pass12345"
        )
        self.operator.assign_role(ROLE_OPERATOR)
        self.product = Product.objects.create(
            name="کاپوچینو",
            tag="نوشیدنی",
            serial_number="2000000000017",
            price_for_company=Decimal("50000"),
            price_for_customer=Decimal("100000"),
            count=10,
        )
        self.sell_payload = {
            "cart_json": json.dumps([{"product_id": self.product.pk, "quantity": 2}]),
            "customer": "مشتری تست",
            "description": "یادداشت",
            "respond_json": "1",
        }
        self.client.login(email="op@f.local", password="pass12345")

    def post_sell(self, action, payload=None, url=None):
        data = dict(self.sell_payload)
        if payload:
            data.update(payload)
        data["action"] = action
        return self.client.post(url or reverse("faktor:sell-create"), data)

    def make_draft(self):
        response = self.post_sell("draft")
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()


class SellFlowTests(FaktorTestBase):
    def test_login_required(self):
        self.client.logout()
        response = self.client.get(reverse("faktor:sell-create"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_empty_cart_rejected(self):
        response = self.client.post(
            reverse("faktor:sell-create"),
            {"cart_json": "[]", "action": "draft", "respond_json": "1"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(FaktorSell.objects.exists())

    def test_unknown_product_rejected(self):
        response = self.client.post(
            reverse("faktor:sell-create"),
            {
                "cart_json": json.dumps([{"product_id": 999999, "quantity": 1}]),
                "action": "draft",
                "respond_json": "1",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(FaktorSell.objects.exists())

    def test_draft_saves_without_changing_stock_or_accountant(self):
        data = self.make_draft()
        invoice = FaktorSell.objects.get(pk=data["id"])
        self.assertEqual(invoice.status, InvoiceStatus.DRAFT)
        self.assertEqual(invoice.number, data["number"])
        self.assertTrue(invoice.number.startswith("S-"))
        self.assertEqual(invoice.total_price, Decimal("200000.00"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.count, 10)
        self.assertFalse(
            AccountantInvoice.objects.using("accountant")
            .filter(kind="sell", source_id=invoice.pk)
            .exists()
        )

    def test_finalize_decrements_stock_and_posts_to_accountant(self):
        data = self.make_draft()
        response = self.post_sell("finalize", url=data["edit_url"])
        self.assertEqual(response.status_code, 200, response.content)
        result = response.json()
        self.assertEqual(result["status"], "completed")

        invoice = FaktorSell.objects.get(pk=data["id"])
        self.assertEqual(invoice.status, InvoiceStatus.COMPLETED)
        self.assertTrue(invoice.accounted)
        self.assertIsNotNone(invoice.completed_at)
        self.product.refresh_from_db()
        self.assertEqual(self.product.count, 8)
        self.assertEqual(invoice.total_price, Decimal("200000.00"))

        accountant = AccountantInvoice.objects.using("accountant").get(
            kind="sell", source_id=invoice.pk
        )
        self.assertEqual(accountant.total, Decimal("200000.00"))
        self.assertEqual(accountant.items.count(), 1)
        self.assertEqual(accountant.items.first().product_name, "کاپوچینو")

    def test_finalize_twice_is_idempotent(self):
        data = self.make_draft()
        self.post_sell("finalize", url=data["edit_url"])
        # دیگر ویرایش مجاز نیست و درخواست دوم فقط خطا می‌دهد
        response = self.post_sell("finalize", url=data["edit_url"])
        self.assertEqual(response.status_code, 400)
        self.product.refresh_from_db()
        self.assertEqual(self.product.count, 8)
        self.assertEqual(
            AccountantInvoice.objects.using("accountant")
            .filter(kind="sell", source_id=data["id"])
            .count(),
            1,
        )

    def test_insufficient_stock_rejected_at_finalize(self):
        data = self.make_draft()
        # موجودی را بعد از پیش‌نویس کم می‌کنیم
        self.product.count = 1
        self.product.save(update_fields=["count"])
        response = self.post_sell("finalize", url=data["edit_url"])
        self.assertEqual(response.status_code, 400)
        error_payload = response.json()
        self.assertTrue(error_payload["draft_saved"])
        self.assertEqual(error_payload["edit_url"], data["edit_url"])
        invoice = FaktorSell.objects.get(pk=data["id"])
        self.assertEqual(invoice.status, InvoiceStatus.DRAFT)
        self.product.refresh_from_db()
        self.assertEqual(self.product.count, 1)

    def test_price_is_not_trusted_from_client(self):
        payload = {
            "cart_json": json.dumps(
                [{"product_id": self.product.pk, "quantity": 1, "unit_price": "1"}]
            )
        }
        data = self.make_draft()
        self.post_sell("finalize", url=data["edit_url"], payload=payload)
        item = FaktorItem.objects.get(sell_id=data["id"])
        self.assertEqual(item.unit_price, self.product.final_price_for_customer())

    def test_print_action_returns_autoprint_url(self):
        response = self.post_sell("print")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("autoprint=1", data["print_url"])
        self.assertTrue(FaktorSell.objects.get(pk=data["id"]).is_completed)

    def test_completed_invoice_cannot_be_edited(self):
        data = self.make_draft()
        self.post_sell("finalize", url=data["edit_url"])
        response = self.client.get(data["edit_url"])
        self.assertRedirects(response, reverse("faktor:sell-preview", args=[data["id"]]))

    def test_operator_cannot_see_another_users_invoice(self):
        data = self.make_draft()
        other = User.objects.create_user(
            email="other@f.local", username="other", password="pass12345"
        )
        other.assign_role(ROLE_OPERATOR)
        self.client.logout()
        self.client.login(email="other@f.local", password="pass12345")
        response = self.client.get(reverse("faktor:sell-preview", args=[data["id"]]))
        self.assertEqual(response.status_code, 404)

    def test_admin_sees_all_invoices(self):
        data = self.make_draft()
        self.client.logout()
        self.client.login(email="admin@f.local", password="pass12345")
        response = self.client.get(reverse("faktor:sell-list"))
        self.assertContains(response, data["number"])

    def test_delete_draft(self):
        data = self.make_draft()
        response = self.client.post(reverse("faktor:sell-delete", args=[data["id"]]))
        self.assertRedirects(response, reverse("faktor:sell-list"))
        self.assertFalse(FaktorSell.objects.filter(pk=data["id"]).exists())

    def test_admin_void_completed_restores_stock(self):
        data = self.make_draft()
        self.post_sell("finalize", url=data["edit_url"])
        self.client.logout()
        self.client.login(email="admin@f.local", password="pass12345")
        response = self.client.post(reverse("faktor:sell-delete", args=[data["id"]]))
        self.assertRedirects(response, reverse("faktor:sell-list"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.count, 10)
        self.assertFalse(FaktorSell.objects.filter(pk=data["id"]).exists())
        accountant = AccountantInvoice.objects.using("accountant").get(
            kind="sell", source_id=data["id"]
        )
        self.assertEqual(accountant.status, AccountantInvoice.STATUS_VOID)

    def test_operator_cannot_void_completed(self):
        data = self.make_draft()
        self.post_sell("finalize", url=data["edit_url"])
        response = self.client.post(reverse("faktor:sell-delete", args=[data["id"]]))
        self.assertRedirects(response, reverse("faktor:sell-preview", args=[data["id"]]))
        self.assertTrue(FaktorSell.objects.filter(pk=data["id"]).exists())


class BuyFlowTests(FaktorTestBase):
    def buy_payload(self, qty=4, price="55000"):
        return {
            "cart_json": json.dumps(
                [{"product_id": self.product.pk, "quantity": qty, "unit_price": price}]
            ),
            "supplier": "تأمین‌کننده",
            "respond_json": "1",
        }

    def test_buy_draft_does_not_change_stock(self):
        response = self.client.post(
            reverse("faktor:buy-create"), {**self.buy_payload(), "action": "draft"}
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.product.refresh_from_db()
        self.assertEqual(self.product.count, 10)
        self.assertEqual(FaktorBuy.objects.get().status, InvoiceStatus.DRAFT)

    def test_buy_finalize_increases_stock_and_updates_cost(self):
        response = self.client.post(
            reverse("faktor:buy-create"), {**self.buy_payload(), "action": "finalize"}
        )
        self.assertEqual(response.status_code, 200, response.content)
        buy = FaktorBuy.objects.get()
        self.assertEqual(buy.status, InvoiceStatus.COMPLETED)
        self.product.refresh_from_db()
        self.assertEqual(self.product.count, 14)
        self.assertEqual(self.product.price_for_company, Decimal("55000.00"))
        self.assertTrue(buy.accounted)
        self.assertTrue(
            AccountantInvoice.objects.using("accountant")
            .filter(kind="buy", source_id=buy.pk)
            .exists()
        )

    def test_completed_buy_cannot_be_deleted(self):
        self.client.post(reverse("faktor:buy-create"), {**self.buy_payload(), "action": "finalize"})
        buy = FaktorBuy.objects.get()
        self.client.logout()
        self.client.login(email="admin@f.local", password="pass12345")
        response = self.client.post(reverse("faktor:buy-delete", args=[buy.pk]))
        self.assertRedirects(response, reverse("faktor:buy-preview", args=[buy.pk]))
        self.assertTrue(FaktorBuy.objects.filter(pk=buy.pk).exists())


class OCRTests(FaktorTestBase):
    def test_parse_common_lines(self):
        text = """
        فاکتور خرید
        قهوه اسپرسو 10 450000
        شیر ۲۴ ۳۸۰۰۰
        لیوان کاغذی 500 12000
        جمع کل 5,000,000
        """
        rows = parse_invoice_text(text)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["name"], "قهوه اسپرسو")
        self.assertEqual(rows[0]["quantity"], 10)
        self.assertEqual(rows[0]["unit_price"], "450000.00")
        self.assertEqual(rows[1]["quantity"], 24)
        self.assertEqual(rows[2]["quantity"], 500)

    def test_parse_line_with_barcode_and_total(self):
        rows = parse_invoice_text("2000000000017 کاپوچینو 3 120000 360000")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["barcode"], "2000000000017")
        self.assertEqual(rows[0]["quantity"], 3)
        self.assertEqual(rows[0]["unit_price"], "120000.00")

    def test_ocr_confirm_creates_product_and_stock(self):
        rows = [
            {"name": "کیک شکلاتی", "barcode": "", "quantity": 5, "unit_price": 90000},
            {"name": "کاپوچینو", "barcode": "", "quantity": 2, "unit_price": 55000},
        ]
        response = self.client.post(
            reverse("faktor:ocr-confirm"),
            {"rows_json": json.dumps(rows, ensure_ascii=False), "supplier": "تأمین‌کننده OCR"},
        )
        self.assertEqual(response.status_code, 302)
        cake = Product.objects.get(name="کیک شکلاتی")
        self.assertEqual(cake.count, 5)
        self.assertEqual(cake.price_for_company, Decimal("90000.00"))
        self.assertGreater(cake.price_for_customer, cake.price_for_company)
        self.product.refresh_from_db()
        self.assertEqual(self.product.count, 12)
        buy = FaktorBuy.objects.get()
        self.assertEqual(buy.status, InvoiceStatus.COMPLETED)
        self.assertEqual(buy.total_price, Decimal("560000.00"))
        self.assertTrue(buy.accounted)

    def test_ocr_confirm_rejects_empty(self):
        response = self.client.post(reverse("faktor:ocr-confirm"), {"rows_json": "[]"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(FaktorBuy.objects.exists())


class ReportsTests(FaktorTestBase):
    def test_reports_kpis(self):
        data = self.make_draft()
        self.post_sell("finalize", url=data["edit_url"])
        self.client.logout()
        self.client.login(email="admin@f.local", password="pass12345")
        response = self.client.get(reverse("reports"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["revenue"], Decimal("200000.00"))
        self.assertEqual(response.context["cost"], Decimal("100000.00"))
        self.assertEqual(response.context["profit"], Decimal("100000.00"))
        self.assertEqual(response.context["sell_count"], 1)
        self.assertEqual(response.context["items_sold"], 2)
        self.assertContains(response, "گزارش فروش")

    def test_reports_export_csv(self):
        data = self.make_draft()
        self.post_sell("finalize", url=data["edit_url"])
        self.client.logout()
        self.client.login(email="admin@f.local", password="pass12345")
        response = self.client.get(reverse("reports-export"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn(data["number"], response.content.decode("utf-8-sig"))
