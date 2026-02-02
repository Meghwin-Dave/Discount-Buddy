"""
Deprecated: use `restaurants.user_urls` and `restaurants.merchant_urls`.

This module keeps a single entrypoint that still enforces `/user/` and `/merchant/`
classification at the path level (regardless of where it's included).
"""

from django.urls import path, include

urlpatterns = [
    path("user/", include("restaurants.user_urls")),
    path("merchant/", include("restaurants.merchant_urls")),
]

