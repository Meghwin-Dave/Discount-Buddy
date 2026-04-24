from rest_framework import serializers
from .models import Notification, DeviceToken


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model"""
    
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
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


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
