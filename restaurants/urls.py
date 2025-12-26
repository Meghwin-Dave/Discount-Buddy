from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CountryListView, CityListView, RestaurantCategoryListView,
    RestaurantViewSet, DealViewSet, DealUseViewSet,
    MerchantRestaurantViewSet, MerchantDealViewSet
)

router = DefaultRouter()
router.register(r"restaurants", RestaurantViewSet, basename="restaurant")
router.register(r"deals", DealViewSet, basename="deal")
router.register(r"deal-uses", DealUseViewSet, basename="deal-use")
router.register(r"merchant/restaurants", MerchantRestaurantViewSet, basename="merchant-restaurant")
router.register(r"merchant/deals", MerchantDealViewSet, basename="merchant-deal")

urlpatterns = [
    path("countries/", CountryListView.as_view(), name="country-list"),
    path("cities/", CityListView.as_view(), name="city-list"),
    path("categories/", RestaurantCategoryListView.as_view(), name="restaurant-category-list"),
    path("", include(router.urls)),
]

