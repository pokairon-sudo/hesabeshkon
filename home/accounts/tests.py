from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from .models import ROLE_ADMIN, ROLE_OPERATOR

User = get_user_model()


def make_user(email, role=None, password="pass12345", **extra):
    user = User.objects.create_user(email=email, password=password, **extra)
    if role:
        user.assign_role(role)
    return user


class AuthTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin@test.local", ROLE_ADMIN, username="admin")
        self.operator = make_user("op@test.local", ROLE_OPERATOR, username="operator")
        self.norole = make_user("norole@test.local", username="norole")

    def test_anonymous_is_redirected_to_login(self):
        for url in ["/", reverse("product:l-product"), reverse("faktor:sell-list"), reverse("reports")]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, url)
            self.assertIn(reverse("login"), response.url)

    def test_login_with_email(self):
        response = self.client.post(
            reverse("login"), {"username": "op@test.local", "password": "pass12345"}
        )
        self.assertRedirects(response, reverse("home"))
        self.assertEqual(str(self.operator.pk), self.client.session["_auth_user_id"])

    def test_user_without_role_cannot_login(self):
        response = self.client.post(
            reverse("login"), {"username": "norole@test.local", "password": "pass12345"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_operator_scope(self):
        self.client.login(email="op@test.local", password="pass12345")
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)
        self.assertEqual(self.client.get(reverse("product:l-product")).status_code, 200)
        self.assertEqual(self.client.get(reverse("faktor:sell-create")).status_code, 200)
        for url in [reverse("reports"), reverse("settings"), reverse("user-list")]:
            response = self.client.get(url)
            self.assertRedirects(response, reverse("home"))

    def test_admin_scope(self):
        self.client.login(email="admin@test.local", password="pass12345")
        for url in [reverse("reports"), reverse("settings"), reverse("user-list")]:
            self.assertEqual(self.client.get(url).status_code, 200)

    def test_admin_panel_is_staff_only(self):
        self.assertEqual(self.client.get("/admin/").status_code, 302)

        self.client.login(email="op@test.local", password="pass12345")
        response = self.client.get("/admin/")
        self.assertRedirects(response, reverse("home"))

        self.client.logout()
        self.client.login(email="admin@test.local", password="pass12345")
        self.assertEqual(self.client.get("/admin/").status_code, 200)

    def test_login_throttled_after_repeated_failures(self):
        cache.clear()
        for _ in range(10):
            response = self.client.post(
                reverse("login"), {"username": "op@test.local", "password": "wrong"}
            )
            self.assertEqual(response.status_code, 400)
        response = self.client.post(
            reverse("login"), {"username": "op@test.local", "password": "pass12345"}
        )
        self.assertEqual(response.status_code, 429)
        cache.clear()

    def test_logout_only_with_post(self):
        self.client.login(email="op@test.local", password="pass12345")
        response = self.client.get(reverse("logout"))
        self.assertRedirects(response, reverse("home"))
        self.assertIn("_auth_user_id", self.client.session)

        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_role_properties_and_groups(self):
        self.assertEqual(self.admin.role, ROLE_ADMIN)
        self.assertTrue(self.admin.is_admin)
        self.assertTrue(self.operator.is_operator)
        self.assertIsNone(self.norole.role)
        self.assertFalse(self.norole.has_app_access)
        self.assertTrue(Group.objects.filter(name=ROLE_ADMIN).exists())
        self.assertTrue(Group.objects.filter(name=ROLE_OPERATOR).exists())

    def test_superuser_is_admin(self):
        superuser = User.objects.create_superuser(
            email="root@test.local", password="pass12345", username="root"
        )
        self.assertEqual(superuser.role, ROLE_ADMIN)
        self.assertTrue(superuser.is_staff)

    def test_assign_role_switches_groups(self):
        self.operator.assign_role(ROLE_ADMIN)
        self.operator.refresh_from_db()
        self.assertEqual(self.operator.role, ROLE_ADMIN)
        self.assertTrue(self.operator.is_staff)
        self.operator.assign_role(ROLE_OPERATOR)
        self.operator.refresh_from_db()
        self.assertEqual(self.operator.role, ROLE_OPERATOR)
        self.assertFalse(self.operator.is_staff)


class UserManagementTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin2@test.local", ROLE_ADMIN, username="admin2")
        self.client.login(email="admin2@test.local", password="pass12345")

    def test_create_operator_via_form(self):
        response = self.client.post(
            reverse("user-create"),
            {
                "username": "newop",
                "email": "newop@test.local",
                "phone": "09121234567",
                "role": ROLE_OPERATOR,
                "password1": "securepass123",
                "password2": "securepass123",
                "is_active": "on",
            },
        )
        self.assertRedirects(response, reverse("user-list"))
        user = User.objects.get(email="newop@test.local")
        self.assertEqual(user.role, ROLE_OPERATOR)
        self.assertTrue(user.check_password("securepass123"))
        self.assertFalse(user.is_staff)

    def test_create_admin_sets_is_staff(self):
        response = self.client.post(
            reverse("user-create"),
            {
                "username": "newadmin",
                "email": "newadmin@test.local",
                "role": ROLE_ADMIN,
                "password1": "securepass123",
                "password2": "securepass123",
                "is_active": "on",
            },
        )
        self.assertRedirects(response, reverse("user-list"))
        user = User.objects.get(email="newadmin@test.local")
        self.assertEqual(user.role, ROLE_ADMIN)
        self.assertTrue(user.is_staff)

    def test_password_mismatch_rejected(self):
        response = self.client.post(
            reverse("user-create"),
            {
                "username": "bad",
                "email": "bad@test.local",
                "role": ROLE_OPERATOR,
                "password1": "securepass123",
                "password2": "different",
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(email="bad@test.local").exists())

    def test_duplicate_email_rejected(self):
        make_user("dup@test.local", ROLE_OPERATOR, username="dup")
        response = self.client.post(
            reverse("user-create"),
            {
                "username": "dup2",
                "email": "dup@test.local",
                "role": ROLE_OPERATOR,
                "password1": "securepass123",
                "password2": "securepass123",
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 400)


class ProfileTests(TestCase):
    def setUp(self):
        self.user = make_user("prof@test.local", ROLE_OPERATOR, username="prof")
        self.client.login(email="prof@test.local", password="pass12345")

    def test_update_profile(self):
        response = self.client.post(
            reverse("profile"),
            {"username": "prof2", "email": "prof@test.local", "phone": "09120000000"},
        )
        self.assertRedirects(response, reverse("profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "prof2")
        self.assertEqual(self.user.phone, "09120000000")

    def test_password_change(self):
        response = self.client.post(
            reverse("password_change"),
            {
                "old_password": "pass12345",
                "new_password1": "brandnewpass999",
                "new_password2": "brandnewpass999",
            },
        )
        self.assertRedirects(response, reverse("password_change_done"))
        self.client.logout()
        self.assertTrue(self.client.login(email="prof@test.local", password="brandnewpass999"))
