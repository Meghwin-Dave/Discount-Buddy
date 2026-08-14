from rest_framework import serializers
from .models import AppConfig, AppBanner, SpinToWinCampaign, SpinToWinItem, UserSpinResult

class AppConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppConfig
        fields = [
            'id', 'config_key', 'config_value', 'config_type', 
            'platform', 'description', 'is_active', 
            'created_at', 'updated_at', 'created_by', 'updated_by'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

class VersionCheckRequestSerializer(serializers.Serializer):
    platform = serializers.ChoiceField(choices=['android', 'ios'])
    version = serializers.CharField(max_length=50)

class VersionCheckResponseSerializer(serializers.Serializer):
    is_update_available = serializers.BooleanField()
    update_type = serializers.CharField()
    is_force_update = serializers.BooleanField()
    is_critical_update = serializers.BooleanField()
    is_optional_update = serializers.BooleanField()
    update_message = serializers.CharField(allow_null=True)
    latest_version = serializers.CharField(allow_null=True)
    minimum_version = serializers.CharField(allow_null=True)
    store_url = serializers.CharField(allow_null=True)


class AppBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppBanner
        fields = [
            "id", "title", "subtitle", "image", "image_url",
            "target_type", "target_value", "display_order", "is_active",
            "start_date", "end_date", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SpinToWinItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpinToWinItem
        fields = [
            "id", "campaign", "title", "description", "icon", "image",
            "item_type", "promo_code_value", "discount_percentage",
            "min_spins_before_win", "stock_limit", "times_won",
            "probability_weight", "slice_index", "is_active",
            "created_at", "updated_at"
        ]
        read_only_fields = ["id", "times_won", "created_at", "updated_at"]


class SpinToWinCampaignSerializer(serializers.ModelSerializer):
    items = SpinToWinItemSerializer(many=True, read_only=True)

    class Meta:
        model = SpinToWinCampaign
        fields = [
            "id", "title", "description", "is_active",
            "max_spins_per_user_per_day", "total_spins_count",
            "items", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "total_spins_count", "created_at", "updated_at"]


class UserSpinResultSerializer(serializers.ModelSerializer):
    item_title = serializers.CharField(source="item.title", read_only=True, default=None)

    class Meta:
        model = UserSpinResult
        fields = [
            "id", "user", "campaign", "item", "item_title",
            "is_win", "promo_code", "spun_at", "claimed_at"
        ]
        read_only_fields = ["id", "spun_at"]

