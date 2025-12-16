from django.urls import path

from .views import WalletDetailView, WalletTransactionsView, WalletTopUpView

urlpatterns = [
    path("", WalletDetailView.as_view(), name="wallet-detail"),
    path("transactions/", WalletTransactionsView.as_view(), name="wallet-transactions"),
    path("topup/", WalletTopUpView.as_view(), name="wallet-topup"),
]


