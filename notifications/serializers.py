from rest_framework import serializers
from django.utils import timezone
from .models import Notification, DeviceToken, AdminNotificationCampaign
from core.serializers_image import ProcessedImageOutputMixin


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model"""
    image = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "title",
            "message",
            "notification_type",
            "is_read",
            "payload",
            "source_id",
            "source_type",
            "image",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_image(self, obj):
        payload = obj.payload or {}
        return payload.get("image")


class DeviceTokenSerializer(serializers.ModelSerializer):
    """Serializer for DeviceToken model"""
    
    class Meta:
        model = DeviceToken
        fields = [
            "id",
            "token",
            "device_type",
            "device_id",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        """
        Create or update device token.
        1. If device_id is provided, find that device and update its token.
        2. If only token is provided, update or create based on token.
        """
        token = validated_data.get("token")
        device_id = validated_data.get("device_id")
        user = self.context["request"].user
        
        if device_id:
            # Prefer matching by device_id to handle token rotations and device migration
            device_token, created = DeviceToken.objects.update_or_create(
                device_id=device_id,
                defaults={
                    "user": user,
                    "token": token,
                    "device_type": validated_data.get("device_type", "android"),
                    "is_active": True,
                }
            )
        else:
            # Fallback to matching by token if device_id is not provided
            device_token, created = DeviceToken.objects.update_or_create(
                token=token,
                defaults={
                    "user": user,
                    "device_type": validated_data.get("device_type", "android"),
                    "is_active": True,
                }
            )
        return device_token


class AdminNotificationCampaignSerializer(ProcessedImageOutputMixin, serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True, allow_null=True, default=None)
    restaurant_slug = serializers.CharField(source="restaurant.slug", read_only=True, allow_null=True, default=None)

    class Meta:
        model = AdminNotificationCampaign
        fields = [
            "id",
            "title",
            "message",
            "image",
            "audience",
            "restaurant",
            "restaurant_name",
            "restaurant_slug",
            "status",
            "scheduled_at",
            "recipient_count",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "recipient_count",
            "error_message",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "image": {"write_only": True, "required": False},
            "restaurant": {"required": False, "allow_null": True},
            "scheduled_at": {"required": False, "allow_null": True},
        }

    def validate_scheduled_at(self, value):
        if value is None:
            return value
        if timezone.is_naive(value):
            value = timezone.make_aware(value, timezone.get_current_timezone())
        if value <= timezone.now():
            raise serializers.ValidationError("Schedule time must be in the future.")
        return value

    def validate_title(self, value):
        title = (value or "").strip()
        if not title:
            raise serializers.ValidationError("Title is required.")
        return title

    def validate_message(self, value):
        message = (value or "").strip()
        if not message:
            raise serializers.ValidationError("Body is required.")
        return message

    def validate(self, attrs):
        audience = attrs.get("audience", AdminNotificationCampaign.AUDIENCE_ALL_CUSTOMERS)
        restaurant = attrs.get("restaurant")
        if audience == AdminNotificationCampaign.AUDIENCE_RESTAURANT_FAVOURITES and not restaurant:
            raise serializers.ValidationError(
                {"restaurant": "Restaurant is required when sending to favourites."}
            )
        return attrs

    def create(self, validated_data):
        if validated_data.get("scheduled_at"):
            validated_data["status"] = AdminNotificationCampaign.STATUS_SCHEDULED
        return super().create(validated_data)

    def to_representation(self, instance):
        from core.utils.datetime_format import to_iso_local

        data = super().to_representation(instance)
        if instance.scheduled_at:
            data["scheduled_at"] = to_iso_local(instance.scheduled_at)
        return data


class AdminNotificationPreviewSerializer(serializers.Serializer):
    audience = serializers.ChoiceField(choices=AdminNotificationCampaign.AUDIENCE_CHOICES)
    restaurant = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        audience = attrs.get("audience")
        restaurant = attrs.get("restaurant")
        if audience == AdminNotificationCampaign.AUDIENCE_RESTAURANT_FAVOURITES and not restaurant:
            raise serializers.ValidationError(
                {"restaurant": "Restaurant is required when sending to favourites."}
            )
        return attrs


class AdminNotificationGenerateSerializer(serializers.Serializer):
    prompt = serializers.CharField()
    audience = serializers.ChoiceField(
        choices=AdminNotificationCampaign.AUDIENCE_CHOICES,
        required=False,
        default=AdminNotificationCampaign.AUDIENCE_ALL_CUSTOMERS,
    )
    restaurant = serializers.IntegerField(required=False, allow_null=True)
