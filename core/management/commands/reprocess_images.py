import logging

from django.apps import apps
from django.core.management.base import BaseCommand

from core.services.image_service import IMAGE_MODEL_REGISTRY, ImageProcessingService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Reprocess existing source images into medium/large WebP variants. "
        "Use for legacy records that still have the original upload field populated."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--model",
            choices=sorted(IMAGE_MODEL_REGISTRY.keys()),
            help="Only reprocess a specific model (e.g. restaurants.restaurantimage).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Reprocess even when medium and large variants already exist.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum number of records to process.",
        )

    def handle(self, *args, **options):
        model_filter = options["model"]
        force = options["force"]
        limit = options["limit"]

        total_processed = 0
        total_skipped = 0

        targets = (
            [model_filter] if model_filter else sorted(IMAGE_MODEL_REGISTRY.keys())
        )

        for model_key in targets:
            app_label, model_name = model_key.split(".")
            model = apps.get_model(app_label, model_name)
            queryset = model.objects.all().order_by("pk")
            if limit is not None:
                queryset = queryset[:limit]

            processed, skipped = ImageProcessingService.reprocess_queryset(
                queryset, force=force
            )

            total_processed += processed
            total_skipped += skipped
            self.stdout.write(
                self.style.SUCCESS(
                    f"{model_key}: processed={processed}, skipped={skipped}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Total processed={total_processed}, skipped={total_skipped}"
            )
        )
