from __future__ import annotations

from datetime import datetime

from core.services.image_service import ImageProcessingService


def _build_processed_path(instance, size: str, filename: str) -> str:
    config = ImageProcessingService.get_config(instance)
    date_path = datetime.now().strftime("%Y/%m/%d")
    return f"{config.upload_prefix}/{size}/{date_path}/{filename}"


def processed_medium_upload_to(instance, filename):
    return _build_processed_path(instance, "medium", filename)


def processed_large_upload_to(instance, filename):
    return _build_processed_path(instance, "large", filename)


# Kept for historical migrations only (removed from active pipeline).
def processed_thumb_upload_to(instance, filename):
    return _build_processed_path(instance, "thumb", filename)


def processed_original_upload_to(instance, filename):
    return _build_processed_path(instance, "original", filename)
