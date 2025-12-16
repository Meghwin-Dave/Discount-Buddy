from rest_framework import serializers

from .models import Voucher, Merchant, VoucherCategory


class VoucherCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = VoucherCategory
        fields = ("id", "name", "slug")


class MerchantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Merchant
        fields = ("id", "name", "verified")


class VoucherSerializer(serializers.ModelSerializer):
    merchant = MerchantSerializer(read_only=True)
    category = VoucherCategorySerializer(read_only=True)

    class Meta:
        model = Voucher
        fields = (
            "id",
            "code",
            "title",
            "description",
            "merchant",
            "category",
            "discount_percent",
            "original_price",
            "sale_price",
            "start_date",
            "end_date",
            "total_quantity",
            "sold_quantity",
            "max_per_user",
            "remaining_quantity",
        )


