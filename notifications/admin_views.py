from rest_framework import viewsets, status
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.permissions import IsSuperUserOrAdmin
from restaurants.models import Restaurant
from core.services.image_service import ImageProcessingService

from .models import AdminNotificationCampaign
from .serializers import (
    AdminNotificationCampaignSerializer,
    AdminNotificationPreviewSerializer,
    AdminNotificationGenerateSerializer,
)
from .services import NotificationService
from .gemini import generate_promo_copy, GeminiUnavailable


class AdminNotificationCampaignViewSet(viewsets.ModelViewSet):
    """Admin compose, preview, and list promotional notification campaigns."""

    serializer_class = AdminNotificationCampaignSerializer
    permission_classes = [IsAuthenticated, IsSuperUserOrAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return AdminNotificationCampaign.objects.select_related("restaurant", "created_by")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @swagger_auto_schema(
        tags=["Admin notifications"],
        operation_summary="Create and send (or schedule) a promo campaign",
        request_body=AdminNotificationCampaignSerializer,
        consumes=["application/json", "multipart/form-data"],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        campaign = serializer.save(created_by=request.user)

        urls = ImageProcessingService.get_image_urls(campaign, request=request)
        image_url = (urls or {}).get("large") or (urls or {}).get("medium") or ""
        if image_url:
            campaign.fcm_image_url = image_url
            campaign.save(update_fields=["fcm_image_url", "updated_at"])

        if not campaign.scheduled_at:
            from .tasks import send_admin_campaign_task
            send_admin_campaign_task.delay(str(campaign.id), campaign.fcm_image_url or None)

        campaign.refresh_from_db()
        output = self.get_serializer(campaign)
        return Response(output.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        method="post",
        tags=["Admin notifications"],
        operation_summary="Preview recipient count",
        request_body=AdminNotificationPreviewSerializer,
    )
    @action(detail=False, methods=["post"], url_path="preview")
    def preview(self, request):
        serializer = AdminNotificationPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        audience = serializer.validated_data["audience"]
        restaurant = None
        restaurant_id = serializer.validated_data.get("restaurant")
        if restaurant_id:
            restaurant = Restaurant.objects.filter(pk=restaurant_id, is_active=True).first()
            if restaurant_id and restaurant is None:
                return Response(
                    {"restaurant": "Restaurant not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        count = NotificationService.resolve_campaign_recipients(audience, restaurant).count()
        return Response({"recipient_count": count})

    @swagger_auto_schema(
        method="post",
        tags=["Admin notifications"],
        operation_summary="Generate title/body with Gemini",
        request_body=AdminNotificationGenerateSerializer,
    )
    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        serializer = AdminNotificationGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        restaurant_name = None
        restaurant_id = serializer.validated_data.get("restaurant")
        if restaurant_id:
            restaurant = Restaurant.objects.filter(pk=restaurant_id).first()
            restaurant_name = restaurant.name if restaurant else None
        try:
            copy = generate_promo_copy(
                serializer.validated_data["prompt"],
                restaurant_name=restaurant_name,
            )
        except GeminiUnavailable as exc:
            return Response(
                {"error": str(exc) or "Gemini is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(copy)
