"""
URL configuration for notifications app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import NotificationViewSet, DeviceTokenViewSet

# Use trailing_slash=False to make custom actions work without trailing slash
# Note: List/detail endpoints will still have trailing slash in URL patterns
router = DefaultRouter(trailing_slash=False)
router.register(r"devices", DeviceTokenViewSet, basename="device-token")
router.register(r"", NotificationViewSet, basename="notification")

urlpatterns = [
    path("", include(router.urls)),
]
