from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CountryListView, CityListView, RestaurantCategoryListView, CuisineListView,
    RestaurantViewSet, DealViewSet, DealUseViewSet,
    MerchantRestaurantViewSet, MerchantDealViewSet,
    # Mobile app views
    HomeScreenView, RestaurantDetailViewSet, ReviewViewSet,
    BookingViewSet, ProfileStatsView,
    # Restaurant management views
    RestaurantManagementViewSet, MenuManagementViewSet,
    OpeningSlotManagementViewSet, RestaurantReviewsManagementView,
    RestaurantBookingsManagementView
)

router = DefaultRouter()
# Public endpoints
router.register(r"restaurants", RestaurantViewSet, basename="restaurant")
router.register(r"restaurant-detail", RestaurantDetailViewSet, basename="restaurant-detail")
router.register(r"deals", DealViewSet, basename="deal")
router.register(r"deal-uses", DealUseViewSet, basename="deal-use")
router.register(r"reviews", ReviewViewSet, basename="review")
router.register(r"bookings", BookingViewSet, basename="booking")
# Merchant/Restaurant management endpoints
router.register(r"merchant/restaurants", MerchantRestaurantViewSet, basename="merchant-restaurant")
router.register(r"merchant/deals", MerchantDealViewSet, basename="merchant-deal")
router.register(r"restaurant/manage", RestaurantManagementViewSet, basename="restaurant-manage")
router.register(r"restaurant/menu", MenuManagementViewSet, basename="menu-manage")
router.register(r"restaurant/opening-slots", OpeningSlotManagementViewSet, basename="opening-slot-manage")

urlpatterns = [
    # Public endpoints
    path("countries/", CountryListView.as_view(), name="country-list"),
    path("cities/", CityListView.as_view(), name="city-list"),
    path("categories/", RestaurantCategoryListView.as_view(), name="restaurant-category-list"),
    path("cuisines/", CuisineListView.as_view(), name="cuisine-list"),
    # Mobile app endpoints
    path("home/", HomeScreenView.as_view(), name="home-screen"),
    path("profile/stats/", ProfileStatsView.as_view(), name="profile-stats"),
    # Restaurant management endpoints
    path("restaurant/reviews/", RestaurantReviewsManagementView.as_view(), name="restaurant-reviews"),
    path("restaurant/bookings/", RestaurantBookingsManagementView.as_view(), name="restaurant-bookings"),
    # Router URLs
    path("", include(router.urls)),
]

