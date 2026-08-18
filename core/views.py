from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from users.permissions import IsSuperUserOrAdmin

from .models import Banner
from .serializers import HealthSerializer, BannerSerializer


class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        serializer = HealthSerializer({"status": "ok"})
        return Response(serializer.data)


class BannerViewSet(viewsets.ReadOnlyModelViewSet):
    """Public customer list of visible home banners (core.Banner)."""

    serializer_class = BannerSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Banner.objects.filter(is_active=True, is_visible=True).order_by(
            "-priority", "-created_at"
        )


class AdminBannerViewSet(viewsets.ModelViewSet):
    """Superadmin CRUD for the same core.Banner records the customer app already shows."""

    serializer_class = BannerSerializer
    permission_classes = [IsSuperUserOrAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        queryset = Banner.objects.filter(is_active=True).order_by("-priority", "-created_at")
        is_visible = self.request.query_params.get("is_visible")
        if is_visible is not None:
            if is_visible.lower() == "true":
                queryset = queryset.filter(is_visible=True)
            elif is_visible.lower() == "false":
                queryset = queryset.filter(is_visible=False)
        return queryset

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.is_visible = False
        instance.save(update_fields=["is_active", "is_visible", "updated_at"])

    @action(detail=True, methods=["post"], url_path="toggle-visible")
    def toggle_visible(self, request, pk=None):
        banner = self.get_object()
        banner.is_visible = not banner.is_visible
        banner.save(update_fields=["is_visible", "updated_at"])
        return Response(
            {
                "status": "success",
                "id": banner.id,
                "is_visible": banner.is_visible,
            },
            status=status.HTTP_200_OK,
        )
