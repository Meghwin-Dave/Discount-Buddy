from django.conf import settings
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Filter,
    FilterExpression,
    Metric,
    RunRealtimeReportRequest,
    RunReportRequest,
)


class GoogleAnalyticsService:
    def __init__(self):
        self.property_id = (getattr(settings, "GA4_PROPERTY_ID", None) or "").strip()
        if not self.property_id:
            raise ValueError("GA4_PROPERTY_ID is not configured")
        self.client = BetaAnalyticsDataClient()

    @property
    def property_name(self):
        return f"properties/{self.property_id}"

    def get_overview(self, start_date="7daysAgo", end_date="today"):
        request = RunReportRequest(
            property=self.property_name,
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            metrics=[
                Metric(name="activeUsers"),
                Metric(name="newUsers"),
                Metric(name="sessions"),
                Metric(name="eventCount"),
                Metric(name="screenPageViews"),
            ],
        )
        response = self.client.run_report(request)
        if not response.rows:
            return {
                "active_users": 0,
                "new_users": 0,
                "sessions": 0,
                "event_count": 0,
                "screen_views": 0,
            }
        row = response.rows[0]
        return {
            "active_users": _metric_int(row, 0),
            "new_users": _metric_int(row, 1),
            "sessions": _metric_int(row, 2),
            "event_count": _metric_int(row, 3),
            "screen_views": _metric_int(row, 4),
        }

    def get_daily_users(self, start_date="30daysAgo", end_date="today"):
        request = RunReportRequest(
            property=self.property_name,
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[Dimension(name="date")],
            metrics=[
                Metric(name="activeUsers"),
                Metric(name="newUsers"),
            ],
        )
        response = self.client.run_report(request)
        rows = [
            {
                "date": row.dimension_values[0].value,
                "active_users": _metric_int(row, 0),
                "new_users": _metric_int(row, 1),
            }
            for row in response.rows
        ]
        return sorted(rows, key=lambda item: item["date"])

    def get_events(self, start_date="7daysAgo", end_date="today"):
        request = RunReportRequest(
            property=self.property_name,
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[Dimension(name="eventName")],
            metrics=[Metric(name="eventCount")],
        )
        response = self.client.run_report(request)
        events = [
            {
                "event_name": row.dimension_values[0].value,
                "count": _metric_int(row, 0),
            }
            for row in response.rows
        ]
        return sorted(events, key=lambda item: item["count"], reverse=True)

    def get_event_count(self, event_name, start_date="7daysAgo", end_date="today"):
        request = RunReportRequest(
            property=self.property_name,
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[Dimension(name="eventName")],
            metrics=[Metric(name="eventCount")],
            dimension_filter=FilterExpression(
                filter=Filter(
                    field_name="eventName",
                    string_filter=Filter.StringFilter(
                        value=event_name,
                        match_type=Filter.StringFilter.MatchType.EXACT,
                    ),
                )
            ),
        )
        response = self.client.run_report(request)
        if not response.rows:
            return 0
        return _metric_int(response.rows[0], 0)

    def get_realtime_users(self):
        request = RunRealtimeReportRequest(
            property=self.property_name,
            metrics=[Metric(name="activeUsers")],
        )
        response = self.client.run_realtime_report(request)
        if not response.rows:
            return 0
        return _metric_int(response.rows[0], 0)

    def get_platform_breakdown(self, start_date="30daysAgo", end_date="today"):
        request = RunReportRequest(
            property=self.property_name,
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[Dimension(name="platform")],
            metrics=[Metric(name="activeUsers")],
        )
        response = self.client.run_report(request)
        return [
            {
                "platform": row.dimension_values[0].value,
                "active_users": _metric_int(row, 0),
            }
            for row in response.rows
        ]

    def get_app_versions(self, start_date="30daysAgo", end_date="today"):
        request = RunReportRequest(
            property=self.property_name,
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[Dimension(name="appVersion")],
            metrics=[Metric(name="activeUsers")],
        )
        response = self.client.run_report(request)
        rows = [
            {
                "version": row.dimension_values[0].value,
                "active_users": _metric_int(row, 0),
            }
            for row in response.rows
        ]
        return sorted(rows, key=lambda item: item["active_users"], reverse=True)

    def get_event_breakdown(
        self,
        event_name: str,
        dimension: str,
        start_date="7daysAgo",
        end_date="today",
        limit: int = 15,
    ):
        request = RunReportRequest(
            property=self.property_name,
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[Dimension(name=dimension)],
            metrics=[Metric(name="eventCount")],
            dimension_filter=FilterExpression(
                filter=Filter(
                    field_name="eventName",
                    string_filter=Filter.StringFilter(
                        value=event_name,
                        match_type=Filter.StringFilter.MatchType.EXACT,
                    ),
                )
            ),
            limit=limit,
        )
        response = self.client.run_report(request)
        rows = [
            {
                "value": row.dimension_values[0].value,
                "count": _metric_int(row, 0),
            }
            for row in response.rows
            if row.dimension_values and row.dimension_values[0].value
        ]
        return sorted(rows, key=lambda item: item["count"], reverse=True)


def _metric_int(row, index):
    try:
        return int(row.metric_values[index].value or 0)
    except (IndexError, TypeError, ValueError):
        return 0
