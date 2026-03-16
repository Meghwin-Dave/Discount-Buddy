from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import AppConfig
from .serializers import AppConfigSerializer, VersionCheckRequestSerializer, VersionCheckResponseSerializer
from .services import AppConfigService

class AppConfigViewSet(viewsets.ModelViewSet):
    queryset = AppConfig.objects.all()
    serializer_class = AppConfigSerializer
    def get_permissions(self):
        if self.action == 'check_version':
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['post'], permission_classes=[AllowAny], url_path='version/check')
    def check_version(self, request):
        try:
            serializer = VersionCheckRequestSerializer(data=request.data)
            if serializer.is_valid():
                platform = serializer.validated_data['platform']
                version = serializer.validated_data['version']
                result = AppConfigService.check_version(platform, version)
                return Response(result, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"FATAL ERROR in check_version: {e}", exc_info=True)
            return Response(
                {"error": "Internal server error occurred while checking version"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
