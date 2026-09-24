"""Notification payload tests for booking timezone handling."""
from datetime import datetime, timezone as dt_timezone

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.utils.datetime_format import to_iso_local
from notifications.services import NotificationService
from restaurants.models import Booking, City, Country, Restaurant

User = get_user_model()


class BookingNotificationTimezoneTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="tz-test-user",
            email="tz-test-user@test.com",
            password="test123",
        )
        self.city = City.objects.create(
            name="London",
            country=Country.objects.create(name="United Kingdom", code="GB"),
            slug="london-tz-test",
        )
        self.restaurant = Restaurant.objects.create(
            name="TZ Test Restaurant",
            slug="tz-test-restaurant",
            city=self.city,
            address="1 Test St",
            verified=True,
            is_active=True,
        )

    def _make_booking(self, utc_hour, month=9, day=9, year=2026):
        booking_date = datetime(year, month, day, utc_hour, 0, tzinfo=dt_timezone.utc)
        return Booking.objects.create(
            user=self.user,
            restaurant=self.restaurant,
            booking_date=booking_date,
            number_of_guests=2,
            status=Booking.STATUS_CONFIRMED,
            contact_name="Test User",
            contact_phone="+440000",
        )

    def test_summer_notification_payload_and_message(self):
        booking = self._make_booking(utc_hour=8)
        notification = NotificationService.send_booking_confirmed(
            user=self.user,
            booking=booking,
        )
        self.assertIn("9:00 AM", notification.message)
        self.assertEqual(
            notification.payload["booking_date"],
            to_iso_local(booking.booking_date),
        )
        self.assertEqual(
            notification.payload["booking_date"],
            "2026-09-09T09:00:00+01:00",
        )

    def test_winter_notification_payload_and_message(self):
        booking = self._make_booking(utc_hour=9, month=1, day=15)
        notification = NotificationService.send_booking_confirmed(
            user=self.user,
            booking=booking,
        )
        self.assertIn("9:00 AM", notification.message)
        self.assertEqual(
            notification.payload["booking_date"],
            "2026-01-15T09:00:00+00:00",
        )


class AdminPromoCampaignTests(TestCase):
    def setUp(self):
        from rest_framework.test import APIClient
        from users.models import UserProfile
        from restaurants.models import SavedRestaurant

        self.SavedRestaurant = SavedRestaurant
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(
            username="promo-admin",
            email="promo-admin@test.com",
            password="adminpassword",
        )
        UserProfile.objects.create(user=self.admin_user, role=UserProfile.ROLE_ADMIN)

        self.customer = User.objects.create_user(
            username="promo-customer",
            email="promo-customer@test.com",
            password="customerpassword",
        )
        UserProfile.objects.create(user=self.customer, role=UserProfile.ROLE_CUSTOMER)

        self.other_customer = User.objects.create_user(
            username="promo-other",
            email="promo-other@test.com",
            password="customerpassword",
        )
        UserProfile.objects.create(user=self.other_customer, role=UserProfile.ROLE_CUSTOMER)

        self.city = City.objects.create(
            name="Manchester",
            country=Country.objects.create(name="England", code="EN"),
            slug="manchester-promo",
        )
        self.restaurant = Restaurant.objects.create(
            name="Promo Pizza",
            slug="promo-pizza",
            city=self.city,
            address="2 Test St",
            verified=True,
            is_active=True,
        )
        SavedRestaurant.objects.create(user=self.customer, restaurant=self.restaurant)

    def test_non_admin_cannot_send(self):
        self.client.force_authenticate(user=self.customer)
        res = self.client.post("/api/v1/admin/admin/notifications/campaigns", {
            "title": "Hello",
            "message": "World",
            "audience": "all_customers",
        })
        self.assertEqual(res.status_code, 403)

    def test_manual_send_all_customers_without_gemini(self):
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.post("/api/v1/admin/admin/notifications/campaigns", {
            "title": "Diwali deals",
            "message": "Festival offers are live",
            "audience": "all_customers",
        })
        self.assertEqual(res.status_code, 201, res.content)
        from notifications.models import Notification
        notes = Notification.objects.filter(notification_type="PROMO")
        self.assertEqual(notes.count(), 2)
        self.assertTrue(all(n.title == "Diwali deals" for n in notes))
        self.assertTrue(all("restaurant_id" not in (n.payload or {}) for n in notes))

    def test_missing_title_is_400(self):
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.post("/api/v1/admin/admin/notifications/campaigns", {
            "title": "  ",
            "message": "Body",
            "audience": "all_customers",
        })
        self.assertEqual(res.status_code, 400)

    def test_favourites_only_saved_users(self):
        self.client.force_authenticate(user=self.admin_user)
        preview = self.client.post("/api/v1/admin/admin/notifications/campaigns/preview", {
            "audience": "restaurant_favourites",
            "restaurant": self.restaurant.id,
        })
        self.assertEqual(preview.status_code, 200, preview.content)
        self.assertEqual(preview.json()["recipient_count"], 1)

        res = self.client.post("/api/v1/admin/admin/notifications/campaigns", {
            "title": "New pizza deal",
            "message": "20% off tonight",
            "audience": "restaurant_favourites",
            "restaurant": self.restaurant.id,
        })
        self.assertEqual(res.status_code, 201, res.content)
        from notifications.models import Notification
        notes = Notification.objects.filter(notification_type="PROMO")
        self.assertEqual(notes.count(), 1)
        self.assertEqual(notes[0].user_id, self.customer.id)
        self.assertEqual(notes[0].payload["restaurant_id"], str(self.restaurant.id))
        self.assertEqual(notes[0].payload["restaurant_slug"], "promo-pizza")

    def test_scheduled_campaign_does_not_send_until_due(self):
        from datetime import timedelta
        from django.utils import timezone
        from notifications.models import Notification, AdminNotificationCampaign
        from notifications.tasks import send_due_admin_campaigns

        self.client.force_authenticate(user=self.admin_user)
        later = timezone.now() + timedelta(hours=2)
        res = self.client.post("/api/v1/admin/admin/notifications/campaigns", {
            "title": "Later pizza",
            "message": "Tonight only",
            "audience": "all_customers",
            "scheduled_at": later.isoformat(),
        })
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()["status"], "scheduled")
        self.assertEqual(Notification.objects.filter(notification_type="PROMO").count(), 0)

        send_due_admin_campaigns()
        self.assertEqual(Notification.objects.filter(notification_type="PROMO").count(), 0)

        campaign = AdminNotificationCampaign.objects.get(pk=res.json()["id"])
        campaign.scheduled_at = timezone.now() - timedelta(minutes=1)
        campaign.save(update_fields=["scheduled_at"])
        send_due_admin_campaigns()
        self.assertEqual(Notification.objects.filter(notification_type="PROMO").count(), 2)
        campaign.refresh_from_db()
        self.assertEqual(campaign.status, "sent")

    def test_past_schedule_is_400(self):
        from datetime import timedelta
        from django.utils import timezone

        self.client.force_authenticate(user=self.admin_user)
        res = self.client.post("/api/v1/admin/admin/notifications/campaigns", {
            "title": "Too late",
            "message": "Already passed",
            "audience": "all_customers",
            "scheduled_at": (timezone.now() - timedelta(minutes=1)).isoformat(),
        })
        self.assertEqual(res.status_code, 400)

    def test_all_customers_with_restaurant_payload(self):
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.post("/api/v1/admin/admin/notifications/campaigns", {
            "title": "Try Promo Pizza",
            "message": "Tap to open the restaurant",
            "audience": "all_customers",
            "restaurant": self.restaurant.id,
        })
        self.assertEqual(res.status_code, 201, res.content)
        from notifications.models import Notification
        notes = list(Notification.objects.filter(notification_type="PROMO"))
        self.assertEqual(len(notes), 2)
        for note in notes:
            self.assertEqual(note.payload["restaurant_id"], str(self.restaurant.id))
            self.assertEqual(note.payload["restaurant_slug"], "promo-pizza")

    def test_generate_without_key_does_not_block_send(self):
        from django.test import override_settings

        self.client.force_authenticate(user=self.admin_user)
        with override_settings(GEMINI_API_KEY=""):
            gen = self.client.post("/api/v1/admin/admin/notifications/campaigns/generate", {
                "prompt": "Diwali festival",
            })
            self.assertEqual(gen.status_code, 503)
        send = self.client.post("/api/v1/admin/admin/notifications/campaigns", {
            "title": "Still works",
            "message": "Manual send",
            "audience": "all_customers",
        })
        self.assertEqual(send.status_code, 201, send.content)

    def test_customer_list_exposes_payload_image(self):
        from notifications.models import Notification
        Notification.objects.create(
            user=self.customer,
            title="Promo",
            message="Hello",
            notification_type="PROMO",
            payload={"image": "https://example.com/promo.webp", "restaurant_id": "1"},
        )
        self.client.force_authenticate(user=self.customer)
        res = self.client.get("/user/api/notifications")
        self.assertEqual(res.status_code, 200, res.content)
        first = res.json()["results"][0]
        self.assertEqual(first["image"], "https://example.com/promo.webp")

