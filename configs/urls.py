from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AppConfigViewSet

router = DefaultRouter()
router.register(r'configs', AppConfigViewSet)

urlpatterns = [
    # Dedicated version check endpoint at /api/app/version/check
    path('version/check', AppConfigViewSet.as_view({'post': 'check_version'}), name='version-check'),
    path('', include(router.urls)),
]
