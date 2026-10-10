"""Regression tests for the review-ownership fix, auth throttling and the
query-count work on the home/list endpoints (responses must stay unchanged)."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient

from restaurants.models import (
    City,
    Country,
    Deal,
    MysteryVisit,
    Restaurant,
    Review,
    SavedRestaurant,
)
from restaurants.services import attach_latest_mystery_visits

User = get_user_model()


def make_user(email):
    return User.objects.create_user(email=email, username=email.split("@")[0], password="pw-12345!")


class ReviewOwnershipTests(TestCase):
    def setUp(self):
        country = Country.objects.create(name="UK", code="GB")
        city = City.objects.create(name="London", country=country, slug="london")
        self.restaurant = Restaurant.objects.create(
            name="R", slug="r", city=city, address="1 St", verified=True
        )
        self.author = make_user("author@example.com")
        self.other = make_user("other@example.com")
        self.review = Review.objects.create(
            user=self.author, restaurant=self.restaurant, rating=4, comment="ok"
        )
        self.url = f"/api/restaurants/reviews/{self.review.id}"

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def test_other_user_cannot_edit_or_delete(self):
        client = self.client_for(self.other)
        self.assertEqual(client.patch(self.url, {"rating": 1}, format="json").status_code, 404)
        self.assertEqual(client.delete(self.url).status_code, 404)
        self.review.refresh_from_db()
        self.assertEqual(self.review.rating, 4)

    def test_author_can_edit_and_delete(self):
        client = self.client_for(self.author)
        self.assertEqual(client.patch(self.url, {"rating": 2}, format="json").status_code, 200)
        self.review.refresh_from_db()
        self.assertEqual(self.review.rating, 2)
        self.assertEqual(client.delete(self.url).status_code, 204)

    def test_reads_stay_public(self):
        anon = APIClient()
        self.assertEqual(anon.get("/api/restaurants/reviews").status_code, 200)
        self.assertEqual(anon.get(self.url).status_code, 200)


class OTPThrottleTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_verify_otp_is_capped_per_email(self):
        client = APIClient()
        email = "victim@example.com"
        client.post("/user/api/users/register/init", {"email": email}, format="json")
        statuses = [
            client.post(
                "/user/api/users/register/verify-otp",
                {"email": email, "otp": "0000"},
                format="json",
                # Different IPs: the per-email cap must hold regardless.
                REMOTE_ADDR=f"10.0.0.{i}",
            ).status_code
            for i in range(12)
        ]
        self.assertEqual(statuses[:10].count(429), 0)
        self.assertEqual(statuses[10:], [429, 429])

    def test_email_cap_is_case_insensitive(self):
        client = APIClient()
        for i in range(10):
            client.post(
                "/user/api/users/register/verify-otp",
                {"email": "Victim@Example.com" if i % 2 else "victim@example.com", "otp": "1"},
                format="json",
            )
        resp = client.post(
            "/user/api/users/register/verify-otp",
            {"email": "VICTIM@example.com", "otp": "1"},
            format="json",
        )
        self.assertEqual(resp.status_code, 429)
        self.assertIn("Too many attempts", resp.json()["detail"])
        self.assertIn("Retry-After", resp.headers)


class HomeQueryCountTests(TestCase):
    def setUp(self):
        country = Country.objects.create(name="UK", code="GB")
        self.city = City.objects.create(name="London", country=country, slug="london")
        self.user = make_user("fan@example.com")
        self.guest = make_user("guest@example.com")

    def make_restaurant(self, i):
        r = Restaurant.objects.create(
            name=f"R{i}", slug=f"r{i}", city=self.city, address="1 St",
            verified=True, latitude=51.5 + i / 100, longitude=-0.12,
        )
        now = timezone.now()
        Deal.objects.create(
            restaurant=r, title="d", start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=1),
        )
        Review.objects.create(user=self.user, restaurant=r, rating=1 + i % 5)
        visit = MysteryVisit.objects.create(
            mystery_guest=self.guest, restaurant=r,
            scheduled_for=now - timedelta(days=10),
            submitted_at=now - timedelta(days=10),
            status=MysteryVisit.STATUS_SUBMITTED, overall_score=80 - i,
        )
        SavedRestaurant.objects.create(user=self.user, restaurant=r)
        return r

    def count_queries(self, url):
        client = APIClient()
        client.force_authenticate(self.user)
        with CaptureQueriesContext(connection) as ctx:
            resp = client.get(url)
        self.assertEqual(resp.status_code, 200)
        return len(ctx), resp.json()

    def test_home_query_count_does_not_grow_with_restaurants(self):
        for i in range(3):
            self.make_restaurant(i)
        small, _ = self.count_queries("/api/restaurants/home?latitude=51.5&longitude=-0.12")
        for i in range(3, 10):
            self.make_restaurant(i)
        large, body = self.count_queries("/api/restaurants/home?latitude=51.5&longitude=-0.12")
        self.assertEqual(small, large)
        self.assertEqual(len(body["sections"]["favourites"]), 10)
        self.assertTrue(all(r["is_favourite"] for r in body["restaurants"].values()))

    def test_list_query_count_does_not_grow_with_restaurants(self):
        for i in range(3):
            self.make_restaurant(i)
        small, _ = self.count_queries("/api/restaurants/restaurants")
        for i in range(3, 10):
            self.make_restaurant(i)
        large, body = self.count_queries("/api/restaurants/restaurants")
        self.assertEqual(small, large)
        self.assertTrue(all(r["is_favourite"] for r in body["results"]))

    def test_bulk_mystery_visit_matches_per_restaurant_lookup(self):
        restaurants = [self.make_restaurant(i) for i in range(4)]
        expected = [r.get_leaderboard_score() for r in restaurants]
        fresh = list(Restaurant.objects.order_by("id"))
        attach_latest_mystery_visits(fresh)
        self.assertEqual([r.get_leaderboard_score() for r in fresh], expected)
        self.assertTrue(all(score > 0 for score in expected))


class DealClaimTests(TestCase):
    """Limits are re-checked under the deal lock. (SQLite ignores row locks, so
    these cover the logic; true concurrency needs Postgres.)"""

    def setUp(self):
        country = Country.objects.create(name="UK", code="GB")
        city = City.objects.create(name="London", country=country, slug="london")
        self.restaurant = Restaurant.objects.create(
            name="R", slug="r", city=city, address="1 St", verified=True
        )
        now = timezone.now()
        self.deal = Deal.objects.create(
            restaurant=self.restaurant, title="d", max_per_user=1, max_uses=2,
            start_date=now - timedelta(days=1), end_date=now + timedelta(days=1),
        )
        self.users = [make_user(f"u{i}@example.com") for i in range(3)]

    def claim(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client.post(f"/api/restaurants/deals/{self.deal.id}/use", {}, format="json")

    def test_claim_creates_code_and_increments_used_count(self):
        resp = self.claim(self.users[0])
        self.assertEqual(resp.status_code, 201)
        self.deal.refresh_from_db()
        self.assertEqual(self.deal.used_count, 1)
        self.assertEqual(len(resp.json()["redemption_code"]), 6)

    def test_per_user_limit(self):
        self.assertEqual(self.claim(self.users[0]).status_code, 201)
        resp = self.claim(self.users[0])
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.json())

    def test_max_uses_cap(self):
        self.assertEqual(self.claim(self.users[0]).status_code, 201)
        self.assertEqual(self.claim(self.users[1]).status_code, 201)
        self.assertEqual(self.claim(self.users[2]).status_code, 400)
        self.deal.refresh_from_db()
        self.assertEqual(self.deal.used_count, 2)

    def test_service_refuses_when_limit_hit_after_precheck(self):
        """The race: view pre-check passed, then another claim landed first."""
        from restaurants.services import DealClaimError, create_deal_use_with_redemption

        stale = Deal.objects.get(pk=self.deal.pk)  # loaded before the other claim
        create_deal_use_with_redemption(user=self.users[0], deal=self.deal)
        create_deal_use_with_redemption(user=self.users[1], deal=self.deal)
        with self.assertRaises(DealClaimError):
            create_deal_use_with_redemption(user=self.users[2], deal=stale)
        self.assertEqual(self.deal.deal_uses.count(), 2)
