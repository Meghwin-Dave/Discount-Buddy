from django.urls import path

from .views import MerchantVoucherView

urlpatterns = [
    path("me", MerchantVoucherView.as_view(), name="merchant-vouchers"),
]

