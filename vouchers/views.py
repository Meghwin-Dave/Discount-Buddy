from django.utils import timezone
from django.core.cache import cache
from rest_framework import generics, permissions, filters

from users.merchant_utils import get_merchant_for_user
from users.permissions import ReadOnly, IsMerchant
from .models import Voucher, Merchant
from .serializers import VoucherSerializer


class VoucherListView(generics.ListAPIView):
    serializer_class = VoucherSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["code", "title", "merchant__name"]
    ordering_fields = ["start_date", "end_date", "sale_price", "discount_percent"]

    def get_queryset(self):
        now = timezone.now()
        cache_key = f"voucher_list_active_{now.date()}"
        qs = cache.get(cache_key)
        if qs is None:
            qs = (
                Voucher.objects.filter(
                    end_date__gte=now, is_active=True, merchant__verified=True
                )
                .select_related("merchant", "category")
                .order_by("-created_at")
            )
            cache.set(cache_key, qs, 60)  # cache 1 minute
        return qs


class MerchantVoucherView(generics.ListCreateAPIView):
    serializer_class = VoucherSerializer
    permission_classes = [IsMerchant | ReadOnly]

    def get_merchant(self):
        return get_merchant_for_user(self.request.user)

    def get_queryset(self):
        return (
            Voucher.objects.filter(merchant__user=self.request.user)
            .select_related("merchant", "category")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        merchant = self.get_merchant()
        serializer.save(merchant=merchant)


