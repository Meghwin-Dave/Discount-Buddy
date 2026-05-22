from datetime import time

from django.test import TestCase

from restaurants.models import City, Country, OpeningSlot, Restaurant
from restaurants.opening_hours_sync import (
    parse_day_hours,
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
