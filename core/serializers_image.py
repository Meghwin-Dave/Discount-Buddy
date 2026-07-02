from rest_framework import serializers

from core.services.image_service import ImageProcessingService


class ProcessedImageOutputMixin:
    """
    Read-only nested image output: { medium, large }.

    Upload still uses the model source field (e.g. `image`) via ModelSerializer.
  Override to_representation to replace the file path with the nested object.
    """

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["image"] = ImageProcessingService.get_image_urls(
            instance, request=self.context.get("request")
        )
        return data


class ProfilePictureOutputMixin:
    """Nested profile picture output: { medium, large }."""

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["profile_picture"] = ImageProcessingService.get_image_urls(
            instance, request=self.context.get("request")
        )
        return data
