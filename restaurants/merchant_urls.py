from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    MerchantRestaurantViewSet,
    MerchantDealViewSet,
    # Restaurant management views
    RestaurantManagementViewSet,
    MenuManagementViewSet,
    MenuItemManagementViewSet,
    OpeningSlotManagementViewSet,
    RestaurantReviewsManagementView,
    RestaurantBookingsManagementViewSet,
    DealRedemptionView,
    MerchantRedemptionHistoryView,
    MerchantDashboardView,
    UpdateOccupancyView,
    RestaurantImageViewSet,
)

router = DefaultRouter(trailing_slash=False)

# Merchant / restaurant management endpoints
router.register(r"restaurants", MerchantRestaurantViewSet, basename="merchant-restaurant")
router.register(r"deals", MerchantDealViewSet, basename="merchant-deal")
router.register(r"restaurant/manage", RestaurantManagementViewSet, basename="restaurant-manage")
router.register(r"restaurant/menu", MenuManagementViewSet, basename="menu-manage")
router.register(r"restaurant/menu-items", MenuItemManagementViewSet, basename="menu-item-manage")
router.register(r"restaurant/bookings", RestaurantBookingsManagementViewSet, basename="restaurant-bookings")
router.register(r"restaurant-images", RestaurantImageViewSet, basename="restaurant-images")
router.register(
    r"restaurant/opening-slots", OpeningSlotManagementViewSet, basename="opening-slot-manage"
)

urlpatterns = [
    # Restaurant management endpoints
    path("dashboard", MerchantDashboardView.as_view(), name="merchant-dashboard"),
    path("restaurant/reviews", RestaurantReviewsManagementView.as_view(), name="restaurant-reviews"),
    path("restaurant/occupancy", UpdateOccupancyView.as_view(), name="restaurant-occupancy"),
    path("deals/redeem", DealRedemptionView.as_view(), name="deal-redeem"),
    path("deals/redemption-history", MerchantRedemptionHistoryView.as_view(), name="merchant-redemption-history"),
    # Router URLs
    path("", include(router.urls)),
]

