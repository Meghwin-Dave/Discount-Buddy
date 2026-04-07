from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import HealthCheckView, BannerViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'banners', BannerViewSet, basename='banner')

urlpatterns = [
    path("health", HealthCheckView.as_view(), name="health-check"),
    path("", include(router.urls)),
]
