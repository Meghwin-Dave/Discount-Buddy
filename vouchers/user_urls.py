from django.urls import path

from .views import VoucherListView

urlpatterns = [
    path("", VoucherListView.as_view(), name="voucher-list"),
]

