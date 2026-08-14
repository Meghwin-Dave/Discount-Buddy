import random
from datetime import datetime
from django.utils import timezone
from django.db import transaction
from django.db.models import F
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from users.permissions import IsSuperUserOrAdmin

from .models import AppConfig, AppBanner, SpinToWinCampaign, SpinToWinItem, UserSpinResult
from .serializers import (
    AppConfigSerializer, VersionCheckRequestSerializer, VersionCheckResponseSerializer,
    AppBannerSerializer, SpinToWinCampaignSerializer, SpinToWinItemSerializer, UserSpinResultSerializer
)
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


# ============================================================================
# Admin API ViewSets (Mobile Admin Panel)
# ============================================================================

class AdminAppBannerViewSet(viewsets.ModelViewSet):
    """Admin ViewSet to manage App Banners"""
    queryset = AppBanner.objects.all()
    serializer_class = AppBannerSerializer
    permission_classes = [IsSuperUserOrAdmin]

    @action(detail=True, methods=["post"], url_path="toggle-active")
    def toggle_active(self, request, pk=None):
        banner = self.get_object()
        banner.is_active = not banner.is_active
        banner.save(update_fields=["is_active", "updated_at"])
        return Response({
            "status": "success",
            "id": banner.id,
            "is_active": banner.is_active
        })


class AdminSpinToWinCampaignViewSet(viewsets.ModelViewSet):
    """Admin ViewSet to manage Spin to Win Campaign settings"""
    queryset = SpinToWinCampaign.objects.all()
    serializer_class = SpinToWinCampaignSerializer
    permission_classes = [IsSuperUserOrAdmin]


class AdminSpinToWinItemViewSet(viewsets.ModelViewSet):
    """Admin ViewSet to manage Spin to Win wheel slice items"""
    queryset = SpinToWinItem.objects.all()
    serializer_class = SpinToWinItemSerializer
    permission_classes = [IsSuperUserOrAdmin]


class AdminSpinHistoryListView(generics.ListAPIView):
    """Admin View to audit spin history and won promo code text messages across users"""
    queryset = UserSpinResult.objects.select_related("user", "campaign", "item").all()
    serializer_class = UserSpinResultSerializer
    permission_classes = [IsSuperUserOrAdmin]


# ============================================================================
# User / Public Mobile API Views
# ============================================================================

from django.db.models import Q


class UserAppBannerListView(generics.ListAPIView):
    """User facing view to get active promotional app banners"""
    serializer_class = AppBannerSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        now = timezone.now()
        qs = AppBanner.objects.filter(is_active=True)
        # Filter by start and end date if set
        qs = qs.filter(Q(start_date__isnull=True) | Q(start_date__lte=now))
        qs = qs.filter(Q(end_date__isnull=True) | Q(end_date__gte=now))
        return qs.order_by("display_order", "-created_at")


class UserSpinToWinWheelView(generics.GenericAPIView):
    """Get active wheel configuration, visible items, and user's remaining spins for today"""
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        campaign = SpinToWinCampaign.objects.filter(is_active=True).first()
        if not campaign:
            return Response(
                {"is_active": False, "message": "No active Spin to Win campaign currently available."},
                status=status.HTTP_200_OK
            )

        items = campaign.items.filter(is_active=True).order_by("slice_index", "id")
        items_data = SpinToWinItemSerializer(items, many=True, context={"request": request}).data

        remaining_spins = campaign.max_spins_per_user_per_day
        if request.user and request.user.is_authenticated:
            today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            user_spins_today = UserSpinResult.objects.filter(
                user=request.user,
                campaign=campaign,
                spun_at__gte=today_start
            ).count()
            remaining_spins = max(0, campaign.max_spins_per_user_per_day - user_spins_today)

        return Response({
            "is_active": True,
            "campaign_id": campaign.id,
            "title": campaign.title,
            "description": campaign.description,
            "max_spins_per_day": campaign.max_spins_per_user_per_day,
            "remaining_spins_today": remaining_spins,
            "slices": items_data
        }, status=status.HTTP_200_OK)


class UserSpinToWinSpinView(generics.GenericAPIView):
    """User performs a spin to win a promo code text message"""
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        campaign = SpinToWinCampaign.objects.filter(is_active=True).first()
        if not campaign:
            return Response({"error": "No active campaign found."}, status=status.HTTP_400_BAD_REQUEST)

        # Check user's daily spin limit
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        spins_today = UserSpinResult.objects.filter(
            user=request.user,
            campaign=campaign,
            spun_at__gte=today_start
        ).count()

        if spins_today >= campaign.max_spins_per_user_per_day:
            return Response(
                {"error": f"You have reached your daily limit of {campaign.max_spins_per_user_per_day} spin(s)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            # Atomically increment total spins count on campaign
            SpinToWinCampaign.objects.filter(pk=campaign.pk).update(total_spins_count=F("total_spins_count") + 1)
            campaign.refresh_from_db(fields=["total_spins_count"])
            current_total_spins = campaign.total_spins_count

            # Fetch active items for this campaign
            active_items = list(campaign.items.filter(is_active=True))
            if not active_items:
                return Response({"error": "No wheel slices available."}, status=status.HTTP_400_BAD_REQUEST)

            # Filter items eligible based on min_spins_before_win threshold AND stock_limit
            eligible_items = [
                item for item in active_items
                if item.min_spins_before_win <= current_total_spins
                and (item.stock_limit is None or item.times_won < item.stock_limit)
            ]

            # If no items met the min_spins_before_win or stock_limit, fall back to empty/try_again items or lowest threshold items
            if not eligible_items:
                eligible_items = [
                    item for item in active_items
                    if item.item_type == SpinToWinItem.ITEM_EMPTY
                ] or active_items

            # Perform weighted random selection
            weights = [item.probability_weight for item in eligible_items]
            selected_item = random.choices(eligible_items, weights=weights, k=1)[0]

            is_win = selected_item.item_type != SpinToWinItem.ITEM_EMPTY
            promo_code_text = selected_item.promo_code_value if is_win else (selected_item.promo_code_value or "Better luck next time!")

            if is_win:
                SpinToWinItem.objects.filter(pk=selected_item.pk).update(times_won=F("times_won") + 1)
                selected_item.refresh_from_db(fields=["times_won"])

            spin_result = UserSpinResult.objects.create(
                user=request.user,
                campaign=campaign,
                item=selected_item,
                is_win=is_win,
                promo_code=promo_code_text,
                spun_at=timezone.now()
            )

        return Response({
            "result_id": spin_result.id,
            "is_win": is_win,
            "slice_index": selected_item.slice_index,
            "title": selected_item.title,
            "item_type": selected_item.item_type,
            "promo_code": promo_code_text,
            "spun_at": spin_result.spun_at
        }, status=status.HTTP_201_CREATED)


class UserSpinToWinMyPrizesView(generics.ListAPIView):
    """Retrieve won promo codes / prizes for the authenticated user"""
    serializer_class = UserSpinResultSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserSpinResult.objects.filter(
            user=self.request.user,
            is_win=True
        ).select_related("item", "campaign").order_by("-spun_at")

