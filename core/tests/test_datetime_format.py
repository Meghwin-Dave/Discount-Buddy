"""Tests for booking datetime helpers (BST/GMT, notifications)."""
from datetime import datetime, timezone as dt_timezone
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.utils import timezone

from core.utils.datetime_format import (
    format_datetime_label,
    to_iso_local,
    to_iso_utc,
)


class BookingDatetimeFormatTests(TestCase):
    """Restaurant-local labels and payloads must follow Europe/London DST rules."""

    def _utc(self, year, month, day, hour, minute=0):
        return datetime(year, month, day, hour, minute, tzinfo=dt_timezone.utc)

    def test_summer_09_00_london_to_iso_local(self):
        """09:00 BST → offset +01:00 in payload."""
        booking = self._utc(2026, 9, 9, 8, 0)
        self.assertEqual(to_iso_local(booking), "2026-09-09T09:00:00+01:00")

    def test_winter_09_00_london_to_iso_local(self):
        """09:00 GMT → offset +00:00 in payload."""
        booking = self._utc(2026, 1, 15, 9, 0)
        self.assertEqual(to_iso_local(booking), "2026-01-15T09:00:00+00:00")

    def test_summer_09_00_london_message_label(self):
        booking = self._utc(2026, 9, 9, 8, 0)
        self.assertIn("9:00 AM", format_datetime_label(booking))
        self.assertIn("September 9, 2026", format_datetime_label(booking))

    def test_winter_09_00_london_message_label(self):
        booking = self._utc(2026, 1, 15, 9, 0)
        self.assertIn("9:00 AM", format_datetime_label(booking))
        self.assertIn("January 15, 2026", format_datetime_label(booking))

    def test_utc_storage_round_trip(self):
        """API stores UTC; local ISO preserves 09:00 wall clock."""
        london = ZoneInfo("Europe/London")
        for year, month, day, utc_hour, offset in (
            (2026, 9, 9, 8, "+01:00"),
            (2026, 1, 15, 9, "+00:00"),
        ):
            utc = datetime(year, month, day, utc_hour, 0, tzinfo=dt_timezone.utc)
            local_iso = to_iso_local(utc)
            self.assertIn("T09:00:00", local_iso)
            self.assertTrue(local_iso.endswith(offset))
            self.assertEqual(to_iso_utc(utc), utc.strftime("%Y-%m-%dT%H:%M:%SZ"))

    def test_serializers_dst_handling(self):
        """Test that serializers output London local time under both BST and GMT."""
        from configs.models import UserSpinResult
        from configs.serializers import UserSpinResultSerializer
        from notifications.models import Notification
        from notifications.serializers import NotificationSerializer
        from restaurants.models import Booking, DealUse, Restaurant
        from restaurants.serializers import (
            BookingSerializer,
            BookingCreateSerializer,
            MerchantBookingListSerializer,
            DealUseSerializer,
        )

        summer_dt = self._utc(2026, 7, 10, 15, 30)  # 16:30 BST (+01:00)
        winter_dt = self._utc(2026, 12, 10, 15, 30)  # 15:30 GMT (+00:00)

        # 1. Spin
        spin_summer = UserSpinResult(spun_at=summer_dt)
        spin_winter = UserSpinResult(spun_at=winter_dt)
        self.assertEqual(UserSpinResultSerializer(spin_summer).data["spun_at"], "2026-07-10T16:30:00+01:00")
        self.assertEqual(UserSpinResultSerializer(spin_winter).data["spun_at"], "2026-12-10T15:30:00+00:00")

        # 2. Notification
        notif_summer = Notification(created_at=summer_dt)
        notif_winter = Notification(created_at=winter_dt)
        self.assertEqual(NotificationSerializer(notif_summer).data["created_at"], "2026-07-10T16:30:00+01:00")
        self.assertEqual(NotificationSerializer(notif_winter).data["created_at"], "2026-12-10T15:30:00+00:00")

        # 3. Booking
        rest = Restaurant.objects.first()
        b_summer = Booking(restaurant=rest, booking_date=summer_dt, created_at=summer_dt, updated_at=summer_dt)
        b_winter = Booking(restaurant=rest, booking_date=winter_dt, created_at=winter_dt, updated_at=winter_dt)
        self.assertEqual(BookingSerializer(b_summer).data["booking_date"], "2026-07-10T16:30:00+01:00")
        self.assertEqual(BookingSerializer(b_winter).data["booking_date"], "2026-12-10T15:30:00+00:00")
        self.assertEqual(BookingCreateSerializer(b_summer).data["booking_date"], "2026-07-10T16:30:00+01:00")
        self.assertEqual(BookingCreateSerializer(b_winter).data["booking_date"], "2026-12-10T15:30:00+00:00")
        self.assertEqual(MerchantBookingListSerializer(b_summer).data["booking_date"], "2026-07-10T16:30:00+01:00")
        self.assertEqual(MerchantBookingListSerializer(b_winter).data["booking_date"], "2026-12-10T15:30:00+00:00")

        # 4. DealUse
        d_summer = DealUse(used_at=summer_dt, created_at=summer_dt)
        d_winter = DealUse(used_at=winter_dt, created_at=winter_dt)
        self.assertEqual(DealUseSerializer(d_summer).data["used_at"], "2026-07-10T16:30:00+01:00")
        self.assertEqual(DealUseSerializer(d_winter).data["used_at"], "2026-12-10T15:30:00+00:00")

    def test_spin_view_response_timestamp(self):
        """UserSpinToWinSpinView payload includes local ISO string with dynamic offset."""
        summer_dt = self._utc(2026, 7, 10, 15, 30)
        winter_dt = self._utc(2026, 12, 10, 15, 30)
        self.assertEqual(to_iso_local(summer_dt), "2026-07-10T16:30:00+01:00")
        self.assertEqual(to_iso_local(winter_dt), "2026-12-10T15:30:00+00:00")
