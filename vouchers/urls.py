"""
Deprecated: use `vouchers.user_urls` and `vouchers.merchant_urls`.

This module keeps a single entrypoint that still enforces `/user/` and `/merchant/`
classification at the path level (regardless of where it's included).
"""

from django.urls import path, include

urlpatterns = [
    path("user/", include("vouchers.user_urls")),
    path("merchant/", include("vouchers.merchant_urls")),
]


