from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AppConfigViewSet,
    AdminAppBannerViewSet,
    AdminSpinToWinCampaignViewSet,
    AdminSpinToWinItemViewSet,
    AdminSpinHistoryListView,
    UserAppBannerListView,
    UserSpinToWinWheelView,
    UserSpinToWinSpinView,
    UserSpinToWinMyPrizesView,
)

router = DefaultRouter(trailing_slash=False)
router.register(r'configs', AppConfigViewSet, basename='config')
router.register(r'admin/banners', AdminAppBannerViewSet, basename='admin-banner')
router.register(r'admin/spin-to-win/campaigns', AdminSpinToWinCampaignViewSet, basename='admin-spin-campaign')
router.register(r'admin/spin-to-win/items', AdminSpinToWinItemViewSet, basename='admin-spin-item')

urlpatterns = [
    # Version check endpoint
    path('version/check', AppConfigViewSet.as_view({'post': 'check_version'}), name='version-check'),

    # Mobile Admin Panel endpoints
    path('admin/spin-to-win/history', AdminSpinHistoryListView.as_view(), name='admin-spin-history'),

    # Mobile User Banners & Spin to Win endpoints
    path('user/banners', UserAppBannerListView.as_view(), name='user-banners'),
    path('user/spin-to-win/wheel', UserSpinToWinWheelView.as_view(), name='user-spin-wheel'),
    path('user/spin-to-win/spin', UserSpinToWinSpinView.as_view(), name='user-spin'),
    path('user/spin-to-win/my-prizes', UserSpinToWinMyPrizesView.as_view(), name='user-spin-prizes'),

    path('', include(router.urls)),
]

