import zoneinfo
from datetime import datetime, time

from django.test import TestCase

from restaurants.models import City, Country, OpeningSlot, Restaurant
from restaurants.opening_hours import build_opening_status, build_weekly_hours
from restaurants.opening_hours_sync import (
    parse_day_hours,
    parse_day_ranges,
    sync_opening_slots_from_opening_hours,
)
from restaurants.serializers import RestaurantSerializer


class OpeningHoursSyncTests(TestCase):
    def setUp(self):
        self.country = Country.objects.create(name="United Kingdom", code="GB")
        self.city = City.objects.create(
            name="London",
            country=self.country,
            slug="london",
        )
        self.restaurant = Restaurant.objects.create(
            name="Test Restaurant",
            slug="test-restaurant",
            city=self.city,
            address="1 Test St",
        )

    def test_parse_string_hours(self):
        opening, closing, is_closed = parse_day_hours("11:00-23:00")
        self.assertFalse(is_closed)
        self.assertEqual(opening, time(11, 0))
        self.assertEqual(closing, time(23, 0))

    def test_parse_dict_hours(self):
        opening, closing, is_closed = parse_day_hours(
            {"open": "09:00", "close": "22:00"}
        )
        self.assertFalse(is_closed)
        self.assertEqual(opening, time(9, 0))
        self.assertEqual(closing, time(22, 0))

    def test_parse_closed(self):
        _, _, is_closed = parse_day_hours("closed")
        self.assertTrue(is_closed)

    def test_sync_creates_opening_slots(self):
        self.restaurant.opening_hours = {
            "monday": "11:00-23:00",
            "friday": "11:00-12:00",
            "sunday": "closed",
        }
        self.restaurant.save(update_fields=["opening_hours"])

        synced = sync_opening_slots_from_opening_hours(self.restaurant)
        self.assertEqual(synced, 3)

        monday = OpeningSlot.objects.get(
            restaurant=self.restaurant, day_of_week=0
        )
        self.assertFalse(monday.is_closed)
        self.assertEqual(monday.opening_time, time(11, 0))
        self.assertEqual(monday.closing_time, time(23, 0))

        friday = OpeningSlot.objects.get(
            restaurant=self.restaurant, day_of_week=4
        )
        self.assertEqual(friday.opening_time, time(11, 0))
        self.assertEqual(friday.closing_time, time(12, 0))

        sunday = OpeningSlot.objects.get(
            restaurant=self.restaurant, day_of_week=6
        )
        self.assertTrue(sunday.is_closed)

    def test_serializer_update_syncs_slots(self):
        serializer = RestaurantSerializer(
            instance=self.restaurant,
            data={
                "opening_hours": {
                    "tuesday": "10:00-20:00",
                    "wednesday": {"open": "09:30", "close": "21:30"},
                }
            },
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        self.assertEqual(
            OpeningSlot.objects.filter(restaurant=self.restaurant).count(), 2
        )
        tuesday = OpeningSlot.objects.get(
            restaurant=self.restaurant, day_of_week=1
        )
        self.assertEqual(tuesday.opening_time, time(10, 0))
        self.assertEqual(tuesday.closing_time, time(20, 0))


class SplitShiftParsingTests(TestCase):
    def test_parse_list_of_range_strings(self):
        self.assertEqual(
            parse_day_ranges(["11:00-15:00", "19:00-22:45"]),
            [(time(11, 0), time(15, 0)), (time(19, 0), time(22, 45))],
        )

    def test_parse_list_of_dicts(self):
        self.assertEqual(
            parse_day_ranges(
                [
                    {"open": "11:00", "close": "15:00"},
                    {"open": "19:00", "close": "22:45"},
                ]
            ),
            [(time(11, 0), time(15, 0)), (time(19, 0), time(22, 45))],
        )

    def test_parse_comma_separated_string(self):
        self.assertEqual(
            parse_day_ranges("11:00-15:00, 19:00-22:45"),
            [(time(11, 0), time(15, 0)), (time(19, 0), time(22, 45))],
        )

    def test_overnight_range_is_kept(self):
        self.assertEqual(parse_day_ranges("22:00-02:00"), [(time(22, 0), time(2, 0))])

    def test_ranges_are_sorted_and_deduplicated(self):
        self.assertEqual(
            parse_day_ranges(["19:00-22:45", "11:00-15:00", "19:00-22:45"]),
            [(time(11, 0), time(15, 0)), (time(19, 0), time(22, 45))],
        )

    def test_closed_markers_yield_no_ranges(self):
        for value in ("", "closed", None, "nonsense"):
            self.assertEqual(parse_day_ranges(value), [], msg=value)


class SplitShiftSyncTests(TestCase):
    def setUp(self):
        self.country = Country.objects.create(name="United Kingdom", code="GB")
        self.city = City.objects.create(
            name="London", country=self.country, slug="london"
        )
        self.restaurant = Restaurant.objects.create(
            name="Split Shift", slug="split-shift", city=self.city, address="1 Test St"
        )

    def test_sync_creates_two_slots_for_one_day(self):
        synced = sync_opening_slots_from_opening_hours(
            self.restaurant, {"wednesday": ["11:00-15:00", "19:00-22:45"]}
        )
        self.assertEqual(synced, 1)

        slots = OpeningSlot.objects.filter(restaurant=self.restaurant, day_of_week=2)
        self.assertEqual(slots.count(), 2)
        self.assertEqual(
            [s.display_range for s in slots.order_by("opening_time")],
            ["11 am\u20133 pm", "7\u201310:45 pm"],
        )

    def test_resync_replaces_previous_slots(self):
        sync_opening_slots_from_opening_hours(
            self.restaurant, {"wednesday": ["11:00-15:00", "19:00-22:45"]}
        )
        sync_opening_slots_from_opening_hours(
            self.restaurant, {"wednesday": "11:00-23:00"}
        )

        slots = OpeningSlot.objects.filter(restaurant=self.restaurant, day_of_week=2)
        self.assertEqual(slots.count(), 1)
        self.assertEqual(slots.first().opening_time, time(11, 0))

    def test_sync_leaves_untouched_days_alone(self):
        sync_opening_slots_from_opening_hours(self.restaurant, {"monday": "09:00-17:00"})
        sync_opening_slots_from_opening_hours(self.restaurant, {"tuesday": "09:00-17:00"})

        self.assertEqual(
            OpeningSlot.objects.filter(restaurant=self.restaurant).count(), 2
        )


class OpeningStatusTests(TestCase):
    """Covers the Google-style status line across the interesting time boundaries."""

    LONDON = zoneinfo.ZoneInfo("Europe/London")

    def setUp(self):
        self.country = Country.objects.create(name="United Kingdom", code="GB")
        self.city = City.objects.create(
            name="London", country=self.country, slug="london"
        )
        self.restaurant = Restaurant.objects.create(
            name="Status Cafe", slug="status-cafe", city=self.city, address="1 Test St"
        )

    def _slot(self, day, opening, closing, is_closed=False):
        return OpeningSlot.objects.create(
            restaurant=self.restaurant,
            day_of_week=day,
            opening_time=opening,
            closing_time=closing,
            is_closed=is_closed,
        )

    def _status_at(self, moment):
        return build_opening_status(
            self.restaurant.opening_slots.all(),
            now=moment.replace(tzinfo=self.LONDON),
        )

    def test_no_slots_returns_none_so_ui_can_hide_the_row(self):
        self.assertIsNone(self._status_at(datetime(2026, 9, 2, 12, 0)))

    def test_open_during_lunch_shows_lunch_closing_time(self):
        self._slot(2, time(11, 0), time(15, 0))
        self._slot(2, time(19, 0), time(22, 45))

        status = self._status_at(datetime(2026, 9, 2, 12, 30))
        self.assertTrue(status["is_open"])
        self.assertEqual(status["label"], "Open \u00b7 Closes 3 pm")

    def test_closed_between_shifts_points_at_dinner(self):
        self._slot(2, time(11, 0), time(15, 0))
        self._slot(2, time(19, 0), time(22, 45))

        status = self._status_at(datetime(2026, 9, 2, 16, 0))
        self.assertFalse(status["is_open"])
        self.assertEqual(status["label"], "Closed \u00b7 Opens 7 pm")

    def test_open_during_dinner_shows_dinner_closing_time(self):
        self._slot(2, time(11, 0), time(15, 0))
        self._slot(2, time(19, 0), time(22, 45))

        status = self._status_at(datetime(2026, 9, 2, 20, 0))
        self.assertEqual(status["label"], "Open \u00b7 Closes 10:45 pm")

    def test_closing_soon_within_final_half_hour(self):
        self._slot(2, time(11, 0), time(15, 0))

        status = self._status_at(datetime(2026, 9, 2, 14, 45))
        self.assertEqual(status["state"], "closing_soon")
        self.assertEqual(status["label"], "Closes soon \u00b7 Closes 3 pm")

    def test_after_last_shift_points_at_next_open_day(self):
        self._slot(2, time(11, 0), time(15, 0))
        self._slot(3, time(11, 0), time(15, 0))

        status = self._status_at(datetime(2026, 9, 2, 23, 0))
        self.assertEqual(status["label"], "Closed \u00b7 Opens 11 am Thu")

    def test_overnight_slot_keeps_restaurant_open_past_midnight(self):
        self._slot(2, time(22, 0), time(2, 0))

        # 00:30 on Thursday is still inside Wednesday's overnight window.
        status = self._status_at(datetime(2026, 9, 3, 0, 30))
        self.assertTrue(status["is_open"])
        self.assertEqual(status["label"], "Open \u00b7 Closes 2 am")

    def test_equal_times_mean_open_all_day(self):
        self._slot(2, time(0, 0), time(0, 0))

        status = self._status_at(datetime(2026, 9, 2, 3, 0))
        self.assertTrue(status["is_open"])
        self.assertEqual(status["label"], "Open 24 hours")

    def test_days_marked_closed_are_ignored(self):
        self._slot(2, time(0, 0), time(0, 0), is_closed=True)
        self._slot(3, time(11, 0), time(15, 0))

        status = self._status_at(datetime(2026, 9, 2, 12, 0))
        self.assertFalse(status["is_open"])
        self.assertEqual(status["label"], "Closed \u00b7 Opens 11 am Thu")

    def test_weekly_hours_start_today_and_group_split_shifts(self):
        self._slot(2, time(11, 0), time(15, 0))
        self._slot(2, time(19, 0), time(22, 45))

        week = build_weekly_hours(
            self.restaurant.opening_slots.all(),
            now=datetime(2026, 9, 2, 12, 0, tzinfo=self.LONDON),
        )

        self.assertEqual(len(week), 7)
        self.assertEqual(week[0]["day_name"], "Wednesday")
        self.assertTrue(week[0]["is_today"])
        self.assertEqual(week[0]["ranges"], ["11 am\u20133 pm", "7\u201310:45 pm"])
        self.assertEqual(week[0]["label"], "11 am\u20133 pm, 7\u201310:45 pm")
        self.assertTrue(week[1]["is_closed"])
        self.assertEqual(week[1]["label"], "Closed")

    def test_is_open_now_respects_split_shifts(self):
        self._slot(2, time(11, 0), time(15, 0))
        self._slot(2, time(19, 0), time(22, 45))

        # Reload so the model reads slots through the same relation the API uses.
        restaurant = Restaurant.objects.get(pk=self.restaurant.pk)
        self.assertIsNotNone(restaurant.get_opening_status())


from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from users.models import User
from restaurants.models import Deal, DealUse, Review


from django.urls import reverse


class RestaurantFilterSortingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.country = Country.objects.create(name="United Kingdom", code="GB")
        self.city = City.objects.create(name="London", country=self.country, slug="london")
        self.user = User.objects.create_user(username="testuser", email="testuser@example.com", password="password123")

        now = timezone.now()
        start = now - timedelta(days=1)
        end = now + timedelta(days=10)

        # R1: 3 deals, 1 claim, rating 4.0
        self.r1 = Restaurant.objects.create(name="R1", slug="r1", city=self.city, is_active=True, verified=True)
        for i in range(3):
            Deal.objects.create(restaurant=self.r1, title=f"R1 Deal {i}", start_date=start, end_date=end, is_active=True)
        DealUse.objects.create(restaurant=self.r1, user=self.user, is_redeemed=True)
        Review.objects.create(restaurant=self.r1, user=self.user, rating=4)

        # R2: 2 deals, 10 claims, rating 3.0
        self.r2 = Restaurant.objects.create(name="R2", slug="r2", city=self.city, is_active=True, verified=True)
        for i in range(2):
            Deal.objects.create(restaurant=self.r2, title=f"R2 Deal {i}", start_date=start, end_date=end, is_active=True)
        for i in range(10):
            u = User.objects.create_user(username=f"user_r2_{i}", email=f"user_r2_{i}@example.com", password="password")
            DealUse.objects.create(restaurant=self.r2, user=u, is_redeemed=True)
        Review.objects.create(restaurant=self.r2, user=self.user, rating=3)

        # R3: 2 deals, 5 claims, rating 5.0
        self.r3 = Restaurant.objects.create(name="R3", slug="r3", city=self.city, is_active=True, verified=True)
        for i in range(2):
            Deal.objects.create(restaurant=self.r3, title=f"R3 Deal {i}", start_date=start, end_date=end, is_active=True)
        for i in range(5):
            u = User.objects.create_user(username=f"user_r3_{i}", email=f"user_r3_{i}@example.com", password="password")
            DealUse.objects.create(restaurant=self.r3, user=u, is_redeemed=True)
        Review.objects.create(restaurant=self.r3, user=self.user, rating=5)

        # R4: 2 deals, 10 claims, rating 4.5
        self.r4 = Restaurant.objects.create(name="R4", slug="r4", city=self.city, is_active=True, verified=True)
        for i in range(2):
            Deal.objects.create(restaurant=self.r4, title=f"R4 Deal {i}", start_date=start, end_date=end, is_active=True)
        for i in range(10):
            u = User.objects.create_user(username=f"user_r4_{i}", email=f"user_r4_{i}@example.com", password="password")
            DealUse.objects.create(restaurant=self.r4, user=u, is_redeemed=True)
        u_rev = User.objects.create_user(username="rev_r4", email="rev_r4@example.com", password="password")
        Review.objects.create(restaurant=self.r4, user=self.user, rating=5)
        Review.objects.create(restaurant=self.r4, user=u_rev, rating=4)  # Avg 4.5

    def test_restaurant_list_sorting_order(self):
        url = reverse("restaurant-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        results = data.get("results", data)
        names = [r["name"] for r in results]

        # Order should be:
        # 1. R1 (3 deals)
        # 2. R4 (2 deals, 10 claims, rating 4.5)
        # 3. R2 (2 deals, 10 claims, rating 3.0)
        # 4. R3 (2 deals, 5 claims, rating 5.0)
        self.assertEqual(names, ["R1", "R4", "R2", "R3"])

