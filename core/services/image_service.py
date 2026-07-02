"""
Centralized image validation and processing.

All upload entry points (API, admin, scripts) route through ImageProcessingService.
Serializers must not contain processing logic.
"""

from __future__ import annotations

import io
import logging
import uuid
from dataclasses import dataclass
from typing import BinaryIO, TYPE_CHECKING

from django.apps import apps
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from PIL import Image, ImageOps, UnidentifiedImageError

from core.exceptions import ImageProcessingError, ImageValidationError

if TYPE_CHECKING:
    from django.db.models import Model

logger = logging.getLogger(__name__)

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "HEIF", "HEIC"}
REJECTED_EXTENSIONS = {".svg"}


@dataclass(frozen=True)
class ImageFieldConfig:
    source_field: str
    medium_field: str
    large_field: str
    upload_prefix: str


IMAGE_MODEL_REGISTRY: dict[str, ImageFieldConfig] = {
    "restaurants.restaurantimage": ImageFieldConfig(
        source_field="image",
        medium_field="image_medium",
        large_field="image_large",
        upload_prefix="restaurants",
    ),
    "restaurants.dealimage": ImageFieldConfig(
        source_field="image",
        medium_field="image_medium",
        large_field="image_large",
        upload_prefix="deals",
    ),
    "restaurants.menuitem": ImageFieldConfig(
        source_field="image",
        medium_field="image_medium",
        large_field="image_large",
        upload_prefix="menu",
    ),
    "core.banner": ImageFieldConfig(
        source_field="image",
        medium_field="image_medium",
        large_field="image_large",
        upload_prefix="banners",
    ),
    "users.userprofile": ImageFieldConfig(
        source_field="profile_picture",
        medium_field="profile_picture_medium",
        large_field="profile_picture_large",
        upload_prefix="profile_pictures",
    ),
}


class ImageProcessingService:
    @classmethod
    def get_config(cls, instance: Model) -> ImageFieldConfig:
        key = f"{instance._meta.app_label}.{instance._meta.model_name}"
        if key not in IMAGE_MODEL_REGISTRY:
            raise ImageProcessingError(f"Model {key} is not registered for image processing.")
        return IMAGE_MODEL_REGISTRY[key]

    @classmethod
    def is_processable_model(cls, instance: Model) -> bool:
        key = f"{instance._meta.app_label}.{instance._meta.model_name}"
        return key in IMAGE_MODEL_REGISTRY

    @classmethod
    def validate_upload(cls, uploaded_file: UploadedFile | BinaryIO) -> None:
        if uploaded_file is None:
            raise ImageValidationError("No image file provided.", code="missing_file")

        filename = getattr(uploaded_file, "name", "") or ""
        extension = f".{filename.rsplit('.', 1)[-1].lower()}" if "." in filename else ""
        if extension in REJECTED_EXTENSIONS:
            raise ImageValidationError(
                "SVG images are not supported.",
                code="unsupported_format",
            )

        max_bytes = settings.IMAGE_MAX_SIZE_MB * 1024 * 1024
        file_size = getattr(uploaded_file, "size", None)
        if file_size is None:
            uploaded_file.seek(0, io.SEEK_END)
            file_size = uploaded_file.tell()
            uploaded_file.seek(0)

        if file_size > max_bytes:
            raise ImageValidationError(
                f"Image exceeds maximum size of {settings.IMAGE_MAX_SIZE_MB} MB.",
                code="file_too_large",
            )

        if file_size == 0:
            raise ImageValidationError("Image file is empty.", code="empty_file")

        uploaded_file.seek(0)
        try:
            with Image.open(uploaded_file) as img:
                img.verify()
        except UnidentifiedImageError as exc:
            raise ImageValidationError(
                "Unsupported or corrupted image file.",
                code="unsupported_format",
            ) from exc
        finally:
            uploaded_file.seek(0)

        uploaded_file.seek(0)
        try:
            with Image.open(uploaded_file) as img:
                fmt = (img.format or "").upper()
                if fmt == "GIF" and getattr(img, "is_animated", False):
                    raise ImageValidationError(
                        "Animated GIF images are not supported.",
                        code="animated_not_supported",
                    )
                if fmt not in ALLOWED_FORMATS and fmt != "GIF":
                    raise ImageValidationError(
                        "Only JPEG, PNG, WebP, and HEIC images are allowed.",
                        code="unsupported_format",
                    )

                width, height = img.size
                if width * height > settings.IMAGE_MAX_PIXELS:
                    raise ImageValidationError(
                        f"Image resolution ({width}x{height}) exceeds the "
                        f"{settings.IMAGE_MAX_PIXELS:,} pixel limit.",
                        code="resolution_too_high",
                    )
        finally:
            uploaded_file.seek(0)

    @classmethod
    def process_upload(cls, instance: Model, uploaded_file: BinaryIO) -> dict[str, ContentFile]:
        """Validate and generate medium + large WebP variants from an upload."""
        cls.validate_upload(uploaded_file)
        return cls.generate_variants(uploaded_file)

    @classmethod
    def handle_new_upload(cls, instance: Model, *, source_changed: bool) -> bool:
        """
        Process a new upload synchronously into medium/large fields.

        Returns True when the upload was processed.
        """
        if not cls.is_processable_model(instance) or not source_changed:
            return False

        config = cls.get_config(instance)
        source_file = getattr(instance, config.source_field, None)
        if not source_file:
            return False

        variants = cls.process_upload(instance, source_file)
        cls._delete_existing_variants(instance, config)
        cls._apply_variants(instance, config, variants)
        cls._clear_source_upload(instance, config)
        return True

    @classmethod
    def generate_variants(cls, source_file: BinaryIO) -> dict[str, ContentFile]:
        source_file.seek(0)
        with Image.open(source_file) as img:
            img = ImageOps.exif_transpose(img)
            img = cls._normalize_color_mode(img)

            base_uuid = uuid.uuid4().hex
            variants: dict[str, ContentFile] = {}

            for size_name in ("medium", "large"):
                max_dim = settings.IMAGE_SIZES[size_name]
                quality = settings.WEBP_QUALITY[size_name]

                resized = img.copy()
                resized.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

                buffer = io.BytesIO()
                save_kwargs = {
                    "format": "WEBP",
                    "quality": quality,
                    "method": settings.WEBP_METHOD,
                    "optimize": True,
                }
                if resized.mode == "RGBA":
                    save_kwargs["lossless"] = False

                resized.save(buffer, **save_kwargs)
                buffer.seek(0)
                variants[size_name] = ContentFile(
                    buffer.read(),
                    name=f"{base_uuid}_{size_name}.webp",
                )

        return variants

    @classmethod
    def get_resolved_file_field(cls, instance: Model, size: str = "large"):
        if not cls.is_processable_model(instance):
            return getattr(instance, "image", None) or getattr(instance, "profile_picture", None)

        config = cls.get_config(instance)
        field_name = config.medium_field if size == "medium" else config.large_field
        resolved = getattr(instance, field_name, None)
        if resolved:
            return resolved

        return getattr(instance, config.source_field, None)

    @classmethod
    def get_resolved_url(cls, instance: Model, size: str = "large", request=None) -> str | None:
        file_field = cls.get_resolved_file_field(instance, size=size)
        if not file_field:
            return None
        if request:
            return request.build_absolute_uri(file_field.url)
        return file_field.url

    @classmethod
    def get_image_urls(cls, instance: Model, request=None) -> dict[str, str | None]:
        return {
            "medium": cls.get_resolved_url(instance, "medium", request),
            "large": cls.get_resolved_url(instance, "large", request),
        }

    @classmethod
    def reprocess_queryset(cls, queryset, *, force: bool = False) -> tuple[int, int]:
        processed = 0
        skipped = 0

        for instance in queryset.iterator():
            config = cls.get_config(instance)
            source_file = getattr(instance, config.source_field, None)
            has_variants = bool(
                getattr(instance, config.medium_field, None)
                and getattr(instance, config.large_field, None)
            )

            if not source_file:
                skipped += 1
                continue

            if has_variants and not force:
                skipped += 1
                continue

            try:
                cls._reprocess_from_source(instance, config, source_file)
                processed += 1
            except Exception:
                logger.exception("Failed to reprocess %s:%s", instance._meta.label, instance.pk)
                skipped += 1

        return processed, skipped

    @classmethod
    def _reprocess_from_source(cls, instance: Model, config: ImageFieldConfig, source_file: BinaryIO) -> None:
        variants = cls.process_upload(instance, source_file)
        cls._delete_existing_variants(instance, config)
        cls._apply_variants(instance, config, variants)
        cls._clear_source_upload(instance, config)
        setattr(instance, "_image_processing_internal", True)
        instance.save()
        setattr(instance, "_image_processing_internal", False)

    @classmethod
    def _apply_variants(cls, instance: Model, config: ImageFieldConfig, variants: dict[str, ContentFile]) -> None:
        getattr(instance, config.medium_field).save(
            variants["medium"].name, variants["medium"], save=False
        )
        getattr(instance, config.large_field).save(
            variants["large"].name, variants["large"], save=False
        )

    @classmethod
    def _delete_existing_variants(cls, instance: Model, config: ImageFieldConfig) -> None:
        for field_name in (config.medium_field, config.large_field):
            field_file = getattr(instance, field_name, None)
            if field_file:
                field_file.delete(save=False)
                setattr(instance, field_name, None)

    @classmethod
    def _clear_source_upload(cls, instance: Model, config: ImageFieldConfig) -> None:
        source_file = getattr(instance, config.source_field, None)
        if source_file:
            try:
                source_file.delete(save=False)
            except Exception:
                pass
        setattr(instance, config.source_field, None)

    @classmethod
    def _normalize_color_mode(cls, img: Image.Image) -> Image.Image:
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            return img.convert("RGBA")
        return img.convert("RGB")

    @classmethod
    def get_instance(cls, app_label: str, model_name: str, pk: int) -> Model:
        model = apps.get_model(app_label, model_name)
        return model.objects.get(pk=pk)

    @classmethod
    @transaction.atomic
    def process_instance_by_key(cls, app_label: str, model_name: str, pk: int) -> None:
        instance = cls.get_instance(app_label, model_name, pk)
        config = cls.get_config(instance)
        source_file = getattr(instance, config.source_field, None)
        if not source_file:
            raise ImageProcessingError("No source image available for reprocessing.")
        cls._reprocess_from_source(instance, config, source_file)
