from rest_framework import serializers


class HealthSerializer(serializers.Serializer):
    status = serializers.CharField()


from .models import Banner

class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = ['id', 'is_visible', 'priority', 'image', 'title', 'body', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

