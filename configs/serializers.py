from rest_framework import serializers
from .models import AppConfig

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
