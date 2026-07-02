from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models

from core.exceptions import ImageValidationError
from core.services.image_service import ImageProcessingService
from core.utils.image_paths import processed_large_upload_to, processed_medium_upload_to


class ProcessedImageBehaviorMixin:
    """Shared save/validation behavior for processed image models."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tracked_source_image_name = self._current_source_image_name()

    def _current_source_image_name(self) -> str | None:
        if not ImageProcessingService.is_processable_model(self):
            return None
        config = ImageProcessingService.get_config(self)
        source = getattr(self, config.source_field, None)
        return source.name if source else None

    def _source_image_changed(self) -> bool:
        if not ImageProcessingService.is_processable_model(self):
            return False

        config = ImageProcessingService.get_config(self)
        source = getattr(self, config.source_field, None)
        if not source:
            return False

        if not self.pk:
            return True

        return source.name != self._tracked_source_image_name

    def clean(self):
        super().clean()
        if not self._source_image_changed():
            return

        config = ImageProcessingService.get_config(self)
        source_file = getattr(self, config.source_field, None)
        if not source_file:
            return

        try:
            ImageProcessingService.validate_upload(source_file)
        except ImageValidationError as exc:
            raise ValidationError({config.source_field: exc.message}) from exc

    def save(self, *args, **kwargs):
        if getattr(self, "_image_processing_internal", False):
            super().save(*args, **kwargs)
            self._tracked_source_image_name = self._current_source_image_name()
            return

        if ImageProcessingService.is_processable_model(self):
            try:
                ImageProcessingService.handle_new_upload(
                    self,
                    source_changed=self._source_image_changed(),
                )
            except ImageValidationError as exc:
                config = ImageProcessingService.get_config(self)
                raise ValidationError({config.source_field: exc.message}) from exc

        super().save(*args, **kwargs)
        self._tracked_source_image_name = self._current_source_image_name()

    def get_image_urls(self, request=None) -> dict[str, str | None]:
        return ImageProcessingService.get_image_urls(self, request=request)


class ProcessedImageMixin(ProcessedImageBehaviorMixin, models.Model):
    """Stores only optimized medium and large WebP variants."""

    image_medium = models.ImageField(
        upload_to=processed_medium_upload_to,
        null=True,
        blank=True,
    )
    image_large = models.ImageField(
        upload_to=processed_large_upload_to,
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True
