from django.db import models
from django.utils import timezone

from core.mixins import ProcessedImageMixin


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        abstract = True

class Banner(ProcessedImageMixin, TimeStampedModel, SoftDeleteModel):
    is_visible = models.BooleanField(default=True)
    priority = models.IntegerField(default=0, help_text="Higher numbers appear first/have higher priority")
    image = models.ImageField(upload_to='banners/', null=True, blank=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    body = models.TextField(null=True, blank=True)
    cta_url = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Tap target: in-app route (e.g. /restaurants/slug) or https URL.",
    )

    class Meta:
        ordering = ['-priority', '-created_at']

    def __str__(self):
        return f"Banner {self.id} - {'Visible' if self.is_visible else 'Hidden'}"

