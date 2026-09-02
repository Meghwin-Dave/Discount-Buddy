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
