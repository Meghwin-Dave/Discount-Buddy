from django.urls import path

from .views import VoucherListView, MerchantVoucherView

urlpatterns = [
    path("", VoucherListView.as_view(), name="voucher-list"),
    path("me/", MerchantVoucherView.as_view(), name="merchant-vouchers"),
]


