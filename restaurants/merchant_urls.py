from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    MerchantRestaurantViewSet,
    MerchantDealViewSet,
    # Restaurant management views
    RestaurantManagementViewSet,
    MenuManagementViewSet,
    OpeningSlotManagementViewSet,
    RestaurantReviewsManagementView,
    RestaurantBookingsManagementView,
    DealRedemptionView,
)

router = DefaultRouter(trailing_slash=False)

# Merchant / restaurant management endpoints
router.register(r"restaurants", MerchantRestaurantViewSet, basename="merchant-restaurant")
router.register(r"deals", MerchantDealViewSet, basename="merchant-deal")
router.register(r"restaurant/manage", RestaurantManagementViewSet, basename="restaurant-manage")
router.register(r"restaurant/menu", MenuManagementViewSet, basename="menu-manage")
router.register(
    r"restaurant/opening-slots", OpeningSlotManagementViewSet, basename="opening-slot-manage"
)

urlpatterns = [
    # Restaurant management endpoints
    path("restaurant/reviews", RestaurantReviewsManagementView.as_view(), name="restaurant-reviews"),
    path("restaurant/bookings", RestaurantBookingsManagementView.as_view(), name="restaurant-bookings"),
    path("deals/redeem", DealRedemptionView.as_view(), name="deal-redeem"),
    # Router URLs
    path("", include(router.urls)),
]

