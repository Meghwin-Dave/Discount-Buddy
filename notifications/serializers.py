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
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        """
        Create or update device token.
        If token already exists, update it and mark as active.
        """
        token = validated_data.get("token")
        user = self.context["request"].user
        
        device_token, created = DeviceToken.objects.update_or_create(
            token=token,
            defaults={
                "user": user,
                "device_type": validated_data.get("device_type", "android"),
                "is_active": True,
            }
        )
        return device_token
