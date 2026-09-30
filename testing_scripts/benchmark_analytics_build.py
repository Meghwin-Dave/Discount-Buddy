"""
Compare cold analytics dashboard build: legacy (sequential GA4) vs current (batch + parallel).

Usage (from repo root, GA4 env configured):
  .venv/bin/python testing_scripts/benchmark_analytics_build.py
"""
import os
import sys
import time

import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "discount_buddy.settings")
django.setup()

from core.services.analytics_dashboard import (  # noqa: E402
    ENGAGEMENT_EVENTS,
    _business_metrics,
    _event_details,
    _build_historical,
    ga_range_to_datetimes,
)
from core.services.google_analytics import GoogleAnalyticsService  # noqa: E402


def _build_historical_legacy(start_date, end_date):
    """Pre-optimization: sequential core reports + sequential engagement details."""
    analytics = GoogleAnalyticsService()
    events = analytics.get_events(start_date=start_date, end_date=end_date)
    counts = {item["event_name"]: item["count"] for item in events}
    window_start, window_end = ga_range_to_datetimes(start_date, end_date)

    engagement = []
    for event_name, label in ENGAGEMENT_EVENTS:
        engagement.append(
            {
                "event_name": event_name,
                "label": label,
                "count": counts.get(event_name, 0),
                "details": _event_details(
                    analytics,
                    event_name,
                    start_date,
                    end_date,
                    window_start,
                    window_end,
                    counts.get(event_name, 0),
                ),
            }
        )

    return {
        "overview": analytics.get_overview(start_date=start_date, end_date=end_date),
        "platforms": analytics.get_platform_breakdown(start_date=start_date, end_date=end_date),
        "app_versions": analytics.get_app_versions(start_date=start_date, end_date=end_date),
        "daily_users": analytics.get_daily_users(start_date=start_date, end_date=end_date),
        "events": events,
        "engagement": engagement,
        "business": _business_metrics(window_start, window_end),
    }


def _timed(label, fn):
    t0 = time.perf_counter()
    fn()
    elapsed = time.perf_counter() - t0
    print(f"{label}: {elapsed:.2f}s")
    return elapsed


def main():
    start_date, end_date = "30daysAgo", "today"
    print("GA4 cold build benchmark (no Django cache; hits Google each run)\n")

    legacy = _timed("Before (sequential GA4)", lambda: _build_historical_legacy(start_date, end_date))
    optimized = _timed("After (batch + parallel)", lambda: _build_historical(start_date, end_date))

    if legacy > 0:
        pct = (1 - optimized / legacy) * 100
        print(f"\nImprovement: {pct:.0f}% faster ({legacy:.2f}s → {optimized:.2f}s)")


if __name__ == "__main__":
    main()
