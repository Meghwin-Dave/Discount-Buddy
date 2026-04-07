from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .serializers import HealthSerializer

from rest_framework import viewsets
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import Banner
from .serializers import HealthSerializer, BannerSerializer


class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        serializer = HealthSerializer({"status": "ok"})
        return Response(serializer.data)


class BannerViewSet(viewsets.ModelViewSet):
    queryset = Banner.objects.filter(is_active=True).order_by('-priority', '-created_at')
    serializer_class = BannerSerializer
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]


    def get_queryset(self):
        queryset = super().get_queryset()
        # Optionally filter by is_visible if provided in query params
        is_visible = self.request.query_params.get('is_visible', None)
        if is_visible is not None:
            if is_visible.lower() == 'true':
                queryset = queryset.filter(is_visible=True)
            elif is_visible.lower() == 'false':
                queryset = queryset.filter(is_visible=False)
        return queryset
