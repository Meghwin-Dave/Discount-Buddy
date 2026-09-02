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
