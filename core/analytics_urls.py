from django.urls import path

from .analytics_views import AnalyticsDashboardAPIView, AnalyticsOverviewAPIView

urlpatterns = [
    path("dashboard", AnalyticsDashboardAPIView.as_view(), name="admin-analytics-dashboard"),
    path("overview", AnalyticsOverviewAPIView.as_view(), name="admin-analytics-overview"),
]
