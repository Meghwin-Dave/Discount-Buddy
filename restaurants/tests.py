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

