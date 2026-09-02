from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from users.models import RegistrationOTP

User = get_user_model()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class DeleteAccountPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="delete-me",
            email="user@example.com",
            password="testpass123",
        )
        self.url = reverse("delete-account")

    def test_page_is_public(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Delete Account")
        self.assertContains(response, "registered email")

    def test_request_shows_otp_step_without_revealing_account(self):
        response = self.client.post(
            self.url,
            {"action": "request", "email": "nobody@example.com"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "verification code")
        self.assertFalse(RegistrationOTP.objects.filter(email="nobody@example.com").exists())

    def test_existing_email_sends_otp_and_deletes_after_confirm(self):
        response = self.client.post(
            self.url,
            {"action": "request", "email": self.user.email},
        )
        self.assertEqual(response.status_code, 200)
        otp = RegistrationOTP.objects.filter(
            email=self.user.email, is_verified=False
        ).latest("created_at")
        self.assertFalse(otp.is_expired)

        confirm = self.client.post(
            self.url,
            {
                "action": "confirm",
                "email": self.user.email,
                "otp": otp.otp_code,
            },
        )
        self.assertEqual(confirm.status_code, 200)
        self.assertContains(confirm, "have been deleted")
        self.assertFalse(User.objects.filter(email=self.user.email).exists())
