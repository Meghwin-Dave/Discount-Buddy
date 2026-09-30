from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from users.models import UserProfile

User = get_user_model()

DASHBOARD_URL = "/api/v1/admin/analytics/dashboard"


def _mock_analytics():
    return {
        "overview": {
            "active_users": 10,
            "new_users": 4,
            "sessions": 12,
            "event_count": 50,
            "screen_views": 20,
        },
        "events": [
            {"event_name": "restaurant_viewed", "count": 8},
            {"event_name": "first_open", "count": 3},
        ],
        "platforms": [{"platform": "Android", "active_users": 7}],
        "app_versions": [{"version": "1.3.4", "active_users": 7}],
        "daily_users": [{"date": "20260924", "active_users": 5, "new_users": 2}],
        "realtime": 6,
    }


class AnalyticsDashboardApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            username="ga4-admin",
            email="ga4-admin@test.com",
            password="adminpassword",
        )
        UserProfile.objects.create(user=self.admin, role=UserProfile.ROLE_ADMIN)
        self.customer = User.objects.create_user(
            username="ga4-customer",
            email="ga4-customer@test.com",
            password="customerpassword",
        )
        UserProfile.objects.create(user=self.customer, role=UserProfile.ROLE_CUSTOMER)

    def _patch_ga(self):
        data = _mock_analytics()
        patcher = patch("core.services.analytics_dashboard.GoogleAnalyticsService")
        mock_cls = patcher.start()
        self.addCleanup(patcher.stop)
        instance = mock_cls.return_value
        instance.get_core_dashboard_bundle.return_value = {
            "overview": data["overview"],
            "events": data["events"],
            "platforms": data["platforms"],
            "app_versions": data["app_versions"],
            "daily_users": data["daily_users"],
        }
        instance.get_realtime_users.return_value = data["realtime"]
        instance.get_event_breakdown.side_effect = Exception("custom dimension unavailable")
        return instance

    def test_non_admin_cannot_view_dashboard(self):
        self.client.force_authenticate(user=self.customer)
        res = self.client.get(DASHBOARD_URL)
        self.assertEqual(res.status_code, 403)

    @override_settings(GA4_PROPERTY_ID="")
    def test_missing_property_id_is_503(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(DASHBOARD_URL)
        self.assertEqual(res.status_code, 503)

    @override_settings(GA4_PROPERTY_ID="524706224")
    def test_dashboard_shape(self):
        self._patch_ga()
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(f"{DASHBOARD_URL}?start_date=7daysAgo&end_date=today")
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertEqual(body["range"]["start_date"], "7daysAgo")
        self.assertEqual(body["overview"]["active_users"], 10)
        self.assertEqual(body["realtime"]["active_users"], 6)
        self.assertEqual(body["behaviour"]["restaurant_views"], 8)
        self.assertEqual(body["behaviour"]["first_opens"], 3)
        event_names = [item["event_name"] for item in body["engagement"]]
        self.assertIn("restaurant_viewed", event_names)
        self.assertIn("app_remove", event_names)
        self.assertIn("deal_viewed", event_names)
        self.assertEqual(body["engagement"][0]["count"], 8)
        self.assertIsInstance(body["engagement"][0]["details"], list)
        self.assertNotIn("restaurant_views", body)
        self.assertIn("bookings_created", body["business"])
        self.assertIn("redemptions", body["business"])
        self.assertIn("top_restaurants", body["business"])
        self.assertEqual(body["platforms"][0]["platform"], "Android")

    @override_settings(GA4_PROPERTY_ID="524706224")
    def test_historical_and_realtime_are_cached(self):
        instance = self._patch_ga()
        self.client.force_authenticate(user=self.admin)
        first = self.client.get(DASHBOARD_URL)
        second = self.client.get(DASHBOARD_URL)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(instance.get_core_dashboard_bundle.call_count, 1)
        self.assertEqual(instance.get_realtime_users.call_count, 1)

    @override_settings(GA4_PROPERTY_ID="524706224")
    def test_engagement_includes_event_parameter_details(self):
        instance = self._patch_ga()
        instance.get_core_dashboard_bundle.return_value = {
            "overview": _mock_analytics()["overview"],
            "events": [
                {"event_name": "login", "count": 6},
                {"event_name": "sign_up", "count": 3},
                {"event_name": "spin_completed", "count": 5},
            ],
            "platforms": _mock_analytics()["platforms"],
            "app_versions": _mock_analytics()["app_versions"],
            "daily_users": _mock_analytics()["daily_users"],
        }

        def breakdown(*, event_name, dimension, start_date, end_date, **kwargs):
            if event_name == "login" and "method" in dimension:
                return [{"value": "google", "count": 4}, {"value": "email", "count": 2}]
            if event_name == "sign_up" and "method" in dimension:
                return [{"value": "email", "count": 3}]
            if event_name == "spin_completed" and "prize_title" in dimension:
                return [{"value": "Free Coffee", "count": 3}]
            raise Exception("custom dimension unavailable")

        instance.get_event_breakdown.side_effect = breakdown
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(DASHBOARD_URL)
        self.assertEqual(res.status_code, 200, res.content)
        by_name = {item["event_name"]: item for item in res.json()["engagement"]}
        self.assertEqual(
            by_name["login"]["details"],
            [{"name": "google", "count": 4}, {"name": "email", "count": 2}],
        )
        self.assertEqual(by_name["sign_up"]["details"], [{"name": "email", "count": 3}])
        self.assertEqual(
            by_name["spin_completed"]["details"],
            [{"name": "Free Coffee", "count": 3}],
        )
