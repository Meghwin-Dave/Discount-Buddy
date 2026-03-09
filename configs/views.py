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
        serializer = VersionCheckRequestSerializer(data=request.data)
        if serializer.is_valid():
            platform = serializer.validated_data['platform']
            version = serializer.validated_data['version']
            result = AppConfigService.check_version(platform, version)
            return Response(result, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
