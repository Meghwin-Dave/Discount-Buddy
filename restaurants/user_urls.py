from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CountryListView,
    CityListView,
    RestaurantCategoryListView,
    CuisineListView,
    RestaurantViewSet,
    DealViewSet,
    DealUseViewSet,
    # Mobile app views
    HomeScreenView,
    RestaurantDetailViewSet,
    ReviewViewSet,
    BookingViewSet,
    ProfileStatsView,
    MysteryVisitViewSet,
)

router = DefaultRouter(trailing_slash=False)

# Public / user-facing endpoints
router.register(r"restaurants", RestaurantViewSet, basename="restaurant")
router.register(r"restaurant-detail", RestaurantDetailViewSet, basename="restaurant-detail")
router.register(r"deals", DealViewSet, basename="deal")
router.register(r"deal-uses", DealUseViewSet, basename="deal-use")
router.register(r"reviews", ReviewViewSet, basename="review")
router.register(r"bookings", BookingViewSet, basename="booking")
router.register(r"mystery-visits", MysteryVisitViewSet, basename="mystery-visit")

urlpatterns = [
    # Public endpoints
    path("countries", CountryListView.as_view(), name="country-list"),
    path("cities", CityListView.as_view(), name="city-list"),
    path("categories", RestaurantCategoryListView.as_view(), name="restaurant-category-list"),
    path("cuisines", CuisineListView.as_view(), name="cuisine-list"),
    # Mobile app endpoints
    path("home", HomeScreenView.as_view(), name="home-screen"),
    path("profile/stats", ProfileStatsView.as_view(), name="profile-stats"),
    # Router URLs
    path("", include(router.urls)),
]

