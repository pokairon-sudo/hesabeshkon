import re

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import mail
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class UserManagerTests(TestCase):
    """T4.1: User creation via the custom UserManager."""

    def test_create_user_hashes_password_and_sets_defaults(self):
        user = User.objects.create_user(
            username="alice", email="alice@example.com", password="secret123"
        )
        self.assertTrue(user.check_password("secret123"))
        self.assertNotEqual(user.password, "secret123")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)

    def test_create_user_requires_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(username="bob", email="", password="x")

    def test_create_user_requires_username(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(username="", email="bob@example.com", password="x")

    def test_create_superuser_sets_staff_and_superuser_flags(self):
        user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="x"
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_new_user_auto_joins_customer_group(self):
        user = User.objects.create_user(
            username="carol", email="carol@example.com", password="x"
        )
        self.assertTrue(user.groups.filter(name="customer").exists())

    def test_is_staff_or_manager_property(self):
        plain = User.objects.create_user(username="p", email="p@example.com", password="x")
        self.assertFalse(plain.is_staff_or_manager)

        grouped = User.objects.create_user(username="g", email="g@example.com", password="x")
        grouped.groups.add(Group.objects.get(name="personal"))
        self.assertTrue(grouped.is_staff_or_manager)

        staffer = User.objects.create_user(username="s2", email="s2@example.com", password="x")
        staffer.is_staff = True
        staffer.save()
        self.assertTrue(staffer.is_staff_or_manager)


class RegistrationLoginTests(TestCase):
    """T4.2: covers the registration form and email-based login (USERNAME_FIELD='email')."""

    def test_registration_creates_user_and_redirects_to_login(self):
        resp = self.client.post(reverse("register"), {
            "username": "newbie", "email": "newbie@example.com",
            "password": "abc12345", "confirm_password": "abc12345", "phone": "",
        })
        self.assertRedirects(resp, reverse("login"))
        self.assertTrue(User.objects.filter(email="newbie@example.com").exists())

    def test_registration_rejects_mismatched_passwords(self):
        resp = self.client.post(reverse("register"), {
            "username": "newbie2", "email": "newbie2@example.com",
            "password": "abc12345", "confirm_password": "DOES-NOT-MATCH", "phone": "",
        })
        self.assertEqual(resp.status_code, 200)  # re-rendered with errors
        self.assertFalse(User.objects.filter(email="newbie2@example.com").exists())
        # T3.3 regression: password must never leak back into the HTML
        # after a validation error (Django's render_value=False guarantee).
        self.assertNotIn(b"DOES-NOT-MATCH", resp.content)

    def test_login_uses_email_not_username(self):
        User.objects.create_user(username="dave", email="dave@example.com", password="pw123456")
        logged_in = self.client.login(email="dave@example.com", password="pw123456")
        self.assertTrue(logged_in)


class ProfileTests(TestCase):
    """T2.3: profile view/edit and password change."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="alice", email="alice@example.com", password="oldpass123"
        )

    def test_anonymous_cannot_view_profile(self):
        resp = self.client.get(reverse("profile"))
        self.assertEqual(resp.status_code, 302)

    def test_update_phone_number(self):
        self.client.login(email="alice@example.com", password="oldpass123")
        resp = self.client.post(reverse("profile"), {
            "username": "alice", "email": "alice@example.com", "phone": "+1234567890",
        })
        self.assertRedirects(resp, reverse("profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, "+1234567890")

    def test_password_change_flow(self):
        self.client.login(email="alice@example.com", password="oldpass123")
        resp = self.client.post(reverse("password_change"), {
            "old_password": "oldpass123",
            "new_password1": "brandnewpass999",
            "new_password2": "brandnewpass999",
        })
        self.assertRedirects(resp, reverse("password_change_done"))

        self.client.logout()
        self.assertFalse(self.client.login(email="alice@example.com", password="oldpass123"))
        self.assertTrue(self.client.login(email="alice@example.com", password="brandnewpass999"))


class PasswordResetFlowTests(TestCase):
    """
    T0.5: full reset flow, including following the *actual* link sent in
    the email — this is what originally caught the {{ url }} template bug
    (the email rendered fine but the link itself was always blank).
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="erin", email="erin@example.com", password="original123"
        )

    def test_reset_email_contains_a_working_link(self):
        resp = self.client.post(reverse("password_reset"), {"email": "erin@example.com"})
        self.assertRedirects(resp, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)

        body = mail.outbox[0].body
        match = re.search(r"(/accounts/reset/\S+)", body)
        self.assertIsNotNone(match, "reset email did not contain a link")
        reset_path = match.group(1)

        resp = self.client.get(reset_path, follow=True)
        self.assertEqual(resp.status_code, 200)
        set_password_path = resp.request["PATH_INFO"]

        resp = self.client.post(set_password_path, {
            "new_password1": "brandnewpass456",
            "new_password2": "brandnewpass456",
        })
        self.assertRedirects(resp, reverse("password_reset_complete"))

        self.assertTrue(
            self.client.login(email="erin@example.com", password="brandnewpass456")
        )
