import math
from django.core.mail import send_mail
from django.conf import settings
from django.db import models
from django.db.models import Q, Count, F, Avg, Sum
from django.utils import timezone
from django.core.cache import cache
from rest_framework import generics, viewsets, status, filters
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import PermissionDenied, ValidationError, NotFound
from users.models import UserProfile
from vouchers.models import Merchant
from .filters import RestaurantFilter, DealFilter
from .models import (
    Country,
    City,
    RestaurantCategory,
    Restaurant,
    Deal,
    SavedRestaurant,
    SavedDeal,
    DealUse,
    Cuisine,
    Review,
    Booking,
    MenuCategory,
    MenuItem,
    OpeningSlot,
    RestaurantProfile,
    MysteryVisit,
    MysteryScore,
    MysteryEvidence,
    Facility,
    RestaurantImage,
    RestaurantPartnerRequest,
    UserRestaurantLoyalty,
    LoyaltyRedemptionRecord,
)
from .serializers import (
    CountrySerializer,
    CitySerializer,
    RestaurantCategorySerializer,
    RestaurantSerializer,
    RestaurantListSerializer,
    DealSerializer,
    DealToggleStatusSerializer,
    DealListSerializer,
    SavedRestaurantSerializer,
    SavedDealSerializer,
    DealUseSerializer,
    DealUseCreateSerializer,
    LoyaltyOnlyUseCreateSerializer,
    DealRedemptionRequestSerializer,
    CuisineSerializer,
    ReviewSerializer,
    ReviewCreateSerializer,
    BookingSerializer,
    BookingCreateSerializer,
    BookingManagementSerializer,
    MerchantBookingListSerializer,
    BookingArriveSerializer,
    BookingNoShowSerializer,
    BookingArriveResponseSerializer,
    BookingNoShowResponseSerializer,
    MenuCategorySerializer,
    MenuItemSerializer,
    MenuItemCreateSerializer,
    OpeningSlotSerializer,
    RestaurantDetailSerializer,
    RestaurantProfileSerializer,
    RestaurantImageSerializer,
    MysteryVisitSerializer,
    MysteryVisitSubmitSerializer,
    MysteryEvidenceSerializer,
    FacilitySerializer,
    RestaurantPartnerRequestSerializer,
    HomeScreenRestaurantSerializer,
    HomeScreenDealSerializer,
    HomeScreenCuisineSerializer,
    UserLoyaltyCardSerializer,
    MerchantLoyaltyCustomerSerializer,
    LoyaltyRedemptionRecordSerializer,
    LoyaltyRewardClaimSerializer,
)
from .services import redeem_deal, calculate_distance, km_to_miles, claim_loyalty_reward, build_loyalty_progress_payload
from users.permissions import (
    IsMerchant,
    IsUser,
    IsRestaurant,
    IsRestaurantOwner,
    IsMysteryGuest,
)

def get_merchant_restaurants_queryset(user):


    """
    Returns a queryset of restaurants that the user is authorized to manage,
    either as an owner profile or via a merchant account.
    """
    from vouchers.models import Merchant
    from django.db.models import Q
    
    merchant, _ = Merchant.objects.get_or_create(
        user=user,
        defaults={'name': user.username or user.email}
    )
    
    return Restaurant.objects.filter(
        Q(merchant=merchant) | Q(owner_profile__user=user)
    ).distinct()



class CountryListView(generics.ListAPIView):
    """List all countries"""
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "code"]
    ordering_fields = ["name"]
    ordering = ["name"]


class CityListView(generics.ListAPIView):
    """List all cities, optionally filtered by country"""
    serializer_class = CitySerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["country", "is_active"]
    search_fields = ["name", "country__name"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]
    
    def get_queryset(self):
        return City.objects.filter(is_active=True).select_related("country").annotate(
            restaurants_count=Count(
                "restaurants",
                filter=Q(restaurants__is_active=True, restaurants__verified=True),
                distinct=True
            )
        )


class RestaurantCategoryListView(generics.ListAPIView):
    """List all restaurant categories"""
    queryset = RestaurantCategory.objects.all()
    serializer_class = RestaurantCategorySerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]


class CuisineListView(generics.ListAPIView):
    """List all cuisines"""
    queryset = Cuisine.objects.filter(is_active=True)
    serializer_class = CuisineSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]


class FacilityListView(generics.ListAPIView):
    """List all restaurant facilities"""
    queryset = Facility.objects.filter(is_active=True)
    serializer_class = FacilitySerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]


class RestaurantViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for restaurants"""
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = RestaurantFilter
    search_fields = ["name", "description", "address", "city__name", "cuisines__name"]
    ordering_fields = ["name", "created_at", "is_featured"]
    ordering = ["-is_featured", "-created_at"]
    lookup_field = "slug"

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs[lookup_url_kwarg]

        # Try to lookup by ID if numeric
        if str(lookup_value).isdigit():
            try:
                return queryset.get(pk=lookup_value)
            except (Restaurant.DoesNotExist, ValueError):
                pass
        
        # Default to lookup by slug
        filter_kwargs = {self.lookup_field: lookup_value}
        try:
            return queryset.get(**filter_kwargs)
        except Restaurant.DoesNotExist:
            raise NotFound(f"No restaurant found with {self.lookup_field} or ID: {lookup_value}")
    
    def get_serializer_class(self):
        if self.action in ["list", "nearby", "discount_buddy"]:
            return RestaurantListSerializer
        return RestaurantDetailSerializer
    
    def get_queryset(self):
        queryset = Restaurant.objects.filter(
            is_active=True,
            verified=True
        ).select_related("city", "city__country")
        
        if self.action == "retrieve":
            queryset = queryset.prefetch_related(
                "categories", "cuisines", "images", "reviews__user", "reviews__user__profile",
                "menu_categories__items", "opening_slots", "deals", "facilities"
            )
        else:
            queryset = queryset.prefetch_related(
                "categories", "images", "facilities", "cuisines"
            )
        
        from django.db.models.functions import Coalesce
        from django.db.models import Value
        
        queryset = queryset.annotate(
            average_rating=Coalesce(Avg("reviews__rating"), Value(0.0), output_field=models.FloatField()),
            reviews_count=Count("reviews", distinct=True),
            active_deals_count=Count(
                "deals",
                filter=Q(
                    deals__is_active=True,
                    deals__start_date__lte=timezone.now(),
                    deals__end_date__gte=timezone.now()
                ),
                distinct=True
            )
        )
        
        # Filter by category slug if provided
        category_slug = self.request.query_params.get("category")
        if category_slug:
            queryset = queryset.filter(categories__slug=category_slug)
        
        # Nearby restaurants (requires lat/long)
        lat = self.request.query_params.get("latitude")
        lon = self.request.query_params.get("longitude")
        # Enforce maximum 100 miles radius
        radius_miles = min(float(self.request.query_params.get("radius", 100)), 100.0)
        radius_km = radius_miles * 1.60934
        
        if lat and lon and self.action in ["list", "nearby", "discount_buddy"]:
            try:
                lat = float(lat)
                lon = float(lon)
                
                # Filter restaurants within approximate radius
                # Simple bounding box filter (not perfect but fast)
                lat_delta = radius_km / 111.0  # roughly 1 degree = 111km
                lon_delta = radius_km / (111.0 * abs(math.cos(math.radians(lat))))
                
                queryset = queryset.filter(
                    latitude__gte=lat - lat_delta,
                    latitude__lte=lat + lat_delta,
                    longitude__gte=lon - lon_delta,
                    longitude__lte=lon + lon_delta,
                    latitude__isnull=False,
                    longitude__isnull=False
                )
            except (ValueError, TypeError):
                pass  # Invalid coordinates, ignore filter
        
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Support latitude/longitude for distance calculation in list view
        lat = request.query_params.get("latitude") or request.query_params.get("lat")
        lon = request.query_params.get("longitude") or request.query_params.get("lon")

        page = self.paginate_queryset(queryset)
        if page is not None:
            if lat and lon:
                for restaurant in page:
                    if restaurant.latitude and restaurant.longitude:
                        try:
                            dist_km = calculate_distance(lat, lon, float(restaurant.latitude), float(restaurant.longitude))
                            if dist_km is not None:
                                restaurant._distance_miles = km_to_miles(dist_km)
                        except (ValueError, TypeError):
                            pass
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        if lat and lon:
            for restaurant in queryset:
                if restaurant.latitude and restaurant.longitude:
                    try:
                        dist_km = calculate_distance(lat, lon, float(restaurant.latitude), float(restaurant.longitude))
                        if dist_km is not None:
                            restaurant._distance_miles = km_to_miles(dist_km)
                    except (ValueError, TypeError):
                        pass

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Calculate distance if coordinates provided
        params = request.query_params
        lat = params.get("latitude") or params.get("lat")
        lon = params.get("longitude") or params.get("lon")
        
        if lat and lon and instance.latitude is not None and instance.longitude is not None:
            try:
                distance = calculate_distance(lat, lon, instance.latitude, instance.longitude)
                if distance is not None:
                    instance._distance = distance
            except (ValueError, TypeError):
                pass
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=True, methods=["post", "delete"], permission_classes=[IsAuthenticated])
    def save(self, request, pk=None):
        """Save or unsave a restaurant"""
        restaurant = self.get_object()
        saved, created = SavedRestaurant.objects.get_or_create(
            user=request.user,
            restaurant=restaurant
        )
        
        if request.method == "DELETE":
            saved.delete()
            return Response({"detail": "Restaurant unsaved"}, status=status.HTTP_204_NO_CONTENT)
        
        serializer = SavedRestaurantSerializer(saved, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated], url_path="loyalty_visit")
    def loyalty_visit(self, request, slug=None):
        """
        Create a loyalty-only visit for the current user at this restaurant.

        Generates a redemption code and QR that the merchant scans via the
        standard deal redemption endpoint to award a loyalty point.
        """
        restaurant = self.get_object()
        serializer = LoyaltyOnlyUseCreateSerializer(
            data={"restaurant": restaurant.id, "notes": request.data.get("notes", "")},
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        deal_use = serializer.save()
        response_serializer = DealUseSerializer(deal_use, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def saved(self, request):
        """Get user's saved restaurants"""
        saved_restaurants = SavedRestaurant.objects.filter(
            user=request.user
        ).select_related("restaurant", "restaurant__city").prefetch_related(
            "restaurant__images"
        ).order_by("-created_at")
        
        restaurants = [sr.restaurant for sr in saved_restaurants]
        serializer = RestaurantListSerializer(restaurants, many=True, context={"request": request})
        return Response(serializer.data)
    
    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def nearby(self, request):
        """
        Get nearby restaurants based on user coordinates, sorted by distance in miles.

        Query params:
        - latitude (required)
        - longitude (required)
        - radius (optional, miles; default 100, max 100)
        """
        lat = request.query_params.get("latitude")
        lon = request.query_params.get("longitude")
        radius_miles = min(float(request.query_params.get("radius", 100)), 100.0)
        
        if not lat or not lon:
            return Response(
                {"error": "latitude and longitude are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            lat = float(lat)
            lon = float(lon)
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid latitude or longitude"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid latitude or longitude"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Convert radius from miles to km for calculations
        radius_km = radius_miles * 1.60934

        # Get all restaurants within bounding box (km)
        lat_delta = radius_km / 111.0
        lon_delta = radius_km / (111.0 * abs(math.cos(math.radians(lat))))
        
        from django.db.models.functions import Coalesce
        from django.db.models import Value

        restaurants = Restaurant.objects.filter(
            is_active=True,
            verified=True,
            latitude__gte=lat - lat_delta,
            latitude__lte=lat + lat_delta,
            longitude__gte=lon - lon_delta,
            longitude__lte=lon + lon_delta,
            latitude__isnull=False,
            longitude__isnull=False
        ).select_related("city", "city__country").prefetch_related(
            "images", "facilities", "categories", "cuisines"
        ).annotate(
            average_rating=Coalesce(Avg("reviews__rating"), Value(0.0), output_field=models.FloatField()),
            reviews_count=Count("reviews", distinct=True),
            active_deals_count=Count(
                "deals",
                filter=Q(
                    deals__is_active=True,
                    deals__start_date__lte=timezone.now(),
                    deals__end_date__gte=timezone.now()
                ),
                distinct=True
            )
        )
        
        # Calculate actual distances and sort
        restaurants_with_distance = []
        for restaurant in restaurants:
            if restaurant.latitude and restaurant.longitude:
                distance_km = calculate_distance(
                    lat, lon,
                    float(restaurant.latitude),
                    float(restaurant.longitude)
                )
                if distance_km:
                    distance_miles = distance_km * 0.621371
                    if distance_miles <= radius_miles:
                        restaurant._distance_miles = distance_miles
                        restaurants_with_distance.append((restaurant, distance_miles))
        
        # Sort by distance
        restaurants_with_distance.sort(key=lambda x: x[1])
        restaurants = [r[0] for r in restaurants_with_distance]
        
        serializer = RestaurantListSerializer(restaurants, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=False, methods=["get"], permission_classes=[AllowAny], url_path="discount-buddy")
    def discount_buddy(self, request):
        """
        Custom action for the Discount-Buddy app.
        Returns restaurants with active deals, filtered by proximity if coordinates are provided.
        """
        lat = request.query_params.get("latitude")
        lon = request.query_params.get("longitude")
        
        # Get baseline queryset with annotations
        queryset = self.get_queryset().filter(
            active_deals_count__gt=0
        )
        
        if lat and lon:
            try:
                lat_float = float(lat)
                lon_float = float(lon)
                # Use standard nearby radius or default to 50 miles
                radius_miles = float(request.query_params.get("radius", 50))
                radius_km = radius_miles * 1.60934
                
                # Bounding box filter
                lat_delta = radius_km / 111.0
                lon_delta = radius_km / (111.0 * abs(math.cos(math.radians(lat_float))))
                
                queryset = queryset.filter(
                    latitude__gte=lat_float - lat_delta,
                    latitude__lte=lat_float + lat_delta,
                    longitude__gte=lon_float - lon_delta,
                    longitude__lte=lon_float + lon_delta
                )
                
                # Full distance calculation for results
                results = []
                for restaurant in queryset:
                    if restaurant.latitude and restaurant.longitude:
                        dist_km = calculate_distance(lat_float, lon_float, float(restaurant.latitude), float(restaurant.longitude))
                        if dist_km and dist_km <= radius_km:
                            restaurant._distance_miles = km_to_miles(dist_km)
                            results.append(restaurant)
                
                # Sort by distance
                results.sort(key=lambda x: getattr(x, '_distance_miles', float('inf')))
                
                page = self.paginate_queryset(results)
                if page is not None:
                    serializer = self.get_serializer(page, many=True)
                    return self.get_paginated_response(serializer.data)
                
                serializer = self.get_serializer(results, many=True)
                return Response(serializer.data)
                
            except (ValueError, TypeError):
                pass
        
        # If no coordinates or error, return default ordered list
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class DealViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for deals"""
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = DealFilter
    search_fields = ["title", "description", "restaurant__name"]
    ordering_fields = ["start_date", "end_date", "created_at", "is_featured"]
    ordering = ["-is_featured", "-created_at"]
    
    def get_serializer_class(self):
        if self.action == "list":
            return DealListSerializer
        return DealSerializer
    
    def get_queryset(self):
        now = timezone.now()
        queryset = Deal.objects.filter(
            is_active=True,
            restaurant__is_active=True,
            restaurant__verified=True
        ).select_related("restaurant", "restaurant__city", "restaurant__city__country").prefetch_related(
            "images"
        ).filter(
            start_date__lte=now,
            end_date__gte=now
        )
        
        # Filter by city
        city = self.request.query_params.get("city")
        if city:
            queryset = queryset.filter(restaurant__city__slug=city)
        
        # Filter by country
        country = self.request.query_params.get("country")
        if country:
            queryset = queryset.filter(restaurant__city__country__code=country)
        
        return queryset
    
    @action(detail=True, methods=["post", "delete"], permission_classes=[IsAuthenticated])
    def save(self, request, pk=None):
        """Save or unsave a deal"""
        deal = self.get_object()
        saved, created = SavedDeal.objects.get_or_create(
            user=request.user,
            deal=deal
        )
        
        if request.method == "DELETE":
            saved.delete()
            return Response({"detail": "Deal unsaved"}, status=status.HTTP_204_NO_CONTENT)
        
        serializer = SavedDealSerializer(saved, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def saved(self, request):
        """Get user's saved deals"""
        saved_deals = SavedDeal.objects.filter(
            user=request.user
        ).select_related("deal", "deal__restaurant").prefetch_related(
            "deal__images"
        ).order_by("-created_at")
        
        deals = [sd.deal for sd in saved_deals]
        serializer = DealListSerializer(deals, many=True, context={"request": request})
        return Response(serializer.data)
    
    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def active(self, request):
        """Get all active deals (cached)"""
        now = timezone.now()
        cache_key = f"active_deals_{now.date()}"
        deals = cache.get(cache_key)
        
        if deals is None:
            deals = Deal.objects.filter(
                is_active=True,
                restaurant__is_active=True,
                restaurant__verified=True,
                start_date__lte=now,
                end_date__gte=now
            ).select_related(
                "restaurant", "restaurant__city"
            ).prefetch_related("images").order_by("-is_featured", "-created_at")
            cache.set(cache_key, list(deals), 300)  # Cache for 5 minutes
        
        serializer = DealListSerializer(deals, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def flash(self, request):
        """Get 'Hot Now' (Flash Deals) - Ending today, high urgency."""
        now = timezone.now()
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        deals = Deal.objects.filter(
            is_active=True,
            restaurant__is_active=True,
            restaurant__verified=True,
            start_date__lte=now,
            end_date__gte=now,
            end_date__lte=today_end
        ).select_related("restaurant", "restaurant__city").prefetch_related("images")

        lat = request.query_params.get("latitude")
        lon = request.query_params.get("longitude")
        
        if lat and lon:
            from .utils import calculate_distance
            try:
                lat = float(lat)
                lon = float(lon)
                deals_with_distance = []
                for deal in deals:
                    dist_km = calculate_distance(
                        lat, lon,
                        float(deal.restaurant.latitude),
                        float(deal.restaurant.longitude)
                    )
                    if dist_km is not None:
                        deal.restaurant._distance_miles = dist_km * 0.621371
                    deals_with_distance.append(deal)
                deals = sorted(deals_with_distance, key=lambda x: getattr(x.restaurant, "_distance_miles", 9999))
            except (ValueError, TypeError):
                deals = deals.order_by("end_date")
        else:
            deals = deals.order_by("end_date")

        serializer = DealListSerializer(deals[:20], many=True, context={"request": request})
        return Response(serializer.data)
    
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def use(self, request, pk=None):
        """
        Claim a deal for the current user.

        This creates a DealUse record, assigns a 6-digit redemption code and
        generates a QR code image that can later be redeemed in the restaurant.
        """
        deal = self.get_object()
        
        if not deal.is_active_now():
            return Response(
                {"error": "This deal is not currently active"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not deal.can_user_use(request.user):
            return Response(
                {"error": "You have reached the maximum uses for this deal"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = DealUseCreateSerializer(
            data={"deal": deal.id, "notes": request.data.get("notes", "")},
            context={"request": request}
        )
        
        if serializer.is_valid():
            deal_use = serializer.save()
            response_serializer = DealUseSerializer(deal_use, context={"request": request})
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DealUseViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for user's deal uses"""
    serializer_class = DealUseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["deal", "restaurant_confirmed"]
    ordering_fields = ["used_at", "created_at"]
    ordering = ["-used_at"]
    
    def get_queryset(self):
        return DealUse.objects.filter(user=self.request.user).select_related(
            "deal", "deal__restaurant", "restaurant"
        )


class MerchantRestaurantViewSet(viewsets.ModelViewSet):
    """ViewSet for merchants to manage their restaurants"""
    serializer_class = RestaurantSerializer
    permission_classes = [IsMerchant]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "address"]
    ordering_fields = ["name", "created_at"]
    ordering = ["-created_at"]
    
    def get_merchant(self):
        # Check if user has merchant role
        try:
            if self.request.user.profile.role != UserProfile.ROLE_MERCHANT:
                raise PermissionDenied("User is not a merchant.")
        except UserProfile.DoesNotExist:
            raise PermissionDenied("User profile not found.")
        
        # Get or create Merchant instance
        merchant, created = Merchant.objects.get_or_create(
            user=self.request.user,
            defaults={'name': self.request.user.username or self.request.user.email}
        )
        return merchant
    
    def get_queryset(self):
        # Get merchant's restaurants
        return get_merchant_restaurants_queryset(self.request.user).select_related(
            "city", "city__country"
        ).prefetch_related(
            "categories", "images"
        ).annotate(
            active_deals_count=Count(
                "deals",
                filter=Q(
                    deals__is_active=True,
                    deals__start_date__lte=timezone.now(),
                    deals__end_date__gte=timezone.now()
                ),
                distinct=True
            )
        )

    
    def perform_create(self, serializer):
        merchant = self.get_merchant()
        serializer.save(merchant=merchant)


class MerchantDealViewSet(viewsets.ModelViewSet):
    """ViewSet for merchants to manage their deals"""
    serializer_class = DealSerializer
    permission_classes = [IsMerchant]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["restaurant", "deal_type", "is_featured"]
    search_fields = ["title", "description"]
    ordering_fields = ["start_date", "end_date", "created_at"]
    ordering = ["-created_at"]
    
    def get_merchant(self):
        # Check if user has merchant role
        try:
            if self.request.user.profile.role != UserProfile.ROLE_MERCHANT:
                raise PermissionDenied("User is not a merchant.")
        except UserProfile.DoesNotExist:
            raise PermissionDenied("User profile not found.")
        
        # Get or create Merchant instance
        merchant, created = Merchant.objects.get_or_create(
            user=self.request.user,
            defaults={'name': self.request.user.username or self.request.user.email}
        )
        return merchant
    
    def get_queryset(self):
        # Get deals for merchant's restaurants
        restaurant_qs = get_merchant_restaurants_queryset(self.request.user)
        return Deal.objects.filter(
            restaurant__in=restaurant_qs
        ).select_related("restaurant").prefetch_related("images")

    
    def perform_create(self, serializer):
        restaurant_id = self.request.data.get("restaurant")
        merchant = self.get_merchant()
        
        # Verify restaurant belongs to merchant
        try:
            restaurant = Restaurant.objects.get(id=restaurant_id, merchant=merchant)
        except Restaurant.DoesNotExist:
            raise ValidationError("Restaurant not found or does not belong to you")
        
        serializer.save(restaurant=restaurant)

    @action(detail=True, methods=["post"])
    def toggle_status(self, request, pk=None):
        """
        Toggle the is_active status of a deal with optional date updates.
        
        Request body (optional):
        {
            "start_date": "2026-05-15T10:00:00Z",  # Optional
            "end_date": "2026-06-15T23:59:59Z"     # Optional
        }
        
        Returns:
        {
            "success": True,
            "is_active": True/False,
            "deal": {...},  # Updated deal details
            "detail": "Deal activated/deactivated successfully.",
            "warnings": [...]  # If any date-related warnings
        }
        """
        deal = self.get_object()
        
        # Validate and parse request data
        serializer = DealToggleStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        start_date = serializer.validated_data.get('start_date')
        end_date = serializer.validated_data.get('end_date')
        
        warnings = []
        
        # If dates are provided, update them
        if start_date or end_date:
            # Use existing dates if not provided
            new_start = start_date or deal.start_date
            new_end = end_date or deal.end_date
            
            # Check if deal is being activated with past end_date
            if end_date and deal.is_active is False:  # User is activating deal
                now = timezone.now()
                if new_end <= now:
                    return Response({
                        "success": False,
                        "detail": "Cannot activate deal: end date must be in the future.",
                        "error_code": "INVALID_END_DATE"
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            deal.start_date = new_start
            deal.end_date = new_end
            
            # If deal is currently inactive and dates are updated, inform user
            if not deal.is_active and (start_date or end_date):
                warnings.append("Deal dates updated. Deal will still be inactive until toggled on.")
        
        # Toggle active status
        deal.is_active = not deal.is_active
        
        # Validate deal can be active
        if deal.is_active:
            now = timezone.now()
            if deal.end_date <= now:
                return Response({
                    "success": False,
                    "detail": "Cannot activate deal: deal's end date has passed.",
                    "error_code": "EXPIRED_DEAL"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if deal.start_date > now:
                warnings.append(f"Deal will become active from {deal.start_date.isoformat()}")
        
        # Save the deal
        deal.save(update_fields=["is_active", "start_date", "end_date", "updated_at"])
        
        # Invalidate active deals cache
        cache.delete(f"active_deals_{timezone.now().date()}")
        
        # Serialize the updated deal
        deal_serializer = DealSerializer(deal, context={"request": request})
        
        response_data = {
            "success": True,
            "is_active": deal.is_active,
            "deal": deal_serializer.data,
            "detail": f"Deal {'activated' if deal.is_active else 'deactivated'} successfully.",
        }
        
        if warnings:
            response_data["warnings"] = warnings
        
        return Response(response_data)



# ==================== MOBILE APP VIEWS ====================

class HomeScreenView(generics.GenericAPIView):
    """
    Home screen API with search, filters, top restaurants, cuisine segregation
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """
        Returns:
        - Search results (if query provided)
        - Now Open & Nearby restaurants
        - Cuisine-based segregation
        - Top 10 in City
        - All Restaurants (Card Format)
        """
        
        # Get query parameters
        params = request.query_params
        search_query = params.get("q", "").strip()
        cuisine_id = params.get("cuisine")
        city_id = params.get("city")
        latitude = params.get("latitude") or params.get("lat")
        longitude = params.get("longitude") or params.get("lon")
        now_open = params.get("now_open", "false").lower() == "true"
        radius_miles = min(float(params.get("radius", 100)), 100.0) # default 100 miles, max 100
        radius_km = radius_miles * 1.60934
        
        # Base queryset
        queryset = Restaurant.objects.filter(
            is_active=True,
            verified=True
        ).select_related("city", "city__country").prefetch_related(
            "categories", "cuisines", "images", "facilities"
        ).annotate(
            average_rating=Avg("reviews__rating"),
            reviews_count=Count("reviews", distinct=True),
            active_deals_count=Count(
                "deals",
                filter=Q(
                    deals__is_active=True,
                    deals__start_date__lte=timezone.now(),
                    deals__end_date__gte=timezone.now()
                ),
                distinct=True
            )
        )
        
        # If coordinates provided, ALWAYS enforce the 100-mile limit globally for this view
        if latitude and longitude:
            try:
                lat = float(latitude)
                lon = float(longitude)
                
                # Bounding box filter (initial coarse filtering)
                lat_delta = radius_km / 111.0
                lon_delta = radius_km / (111.0 * abs(math.cos(math.radians(lat))))
                
                queryset = queryset.filter(
                    latitude__gte=lat - lat_delta,
                    latitude__lte=lat + lat_delta,
                    longitude__gte=lon - lon_delta,
                    longitude__lte=lon + lon_delta,
                    latitude__isnull=False,
                    longitude__isnull=False
                )
            except (ValueError, TypeError):
                pass
        
        # Filter by city
        if city_id:
            try:
                queryset = queryset.filter(city_id=city_id)
            except ValueError:
                pass
        
        # Search filter
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(address__icontains=search_query) |
                Q(cuisines__name__icontains=search_query) |
                Q(categories__name__icontains=search_query)
            ).distinct()
        
        # Filter by cuisine
        if cuisine_id:
            queryset = queryset.filter(cuisines__id=cuisine_id)
        
        # Trending Near You - limited to 10 miles
        nearby_restaurants = []
        if latitude and longitude:
            try:
                lat = float(latitude)
                lon = float(longitude)
                trending_radius_miles = 10.0
                trending_radius_km = trending_radius_miles * 1.60934
                
                # Bounding box filter for trending
                trend_lat_delta = trending_radius_km / 111.0
                trend_lon_delta = trending_radius_km / (111.0 * abs(math.cos(math.radians(lat))))
                
                nearby_qs = queryset.filter(
                    latitude__gte=lat - trend_lat_delta,
                    latitude__lte=lat + trend_lat_delta,
                    longitude__gte=lon - trend_lon_delta,
                    longitude__lte=lon + trend_lon_delta
                )
                
                # Calculate distances and filter by exact radius
                restaurants_with_distance = []
                for restaurant in nearby_qs:
                    dist_km = calculate_distance(
                        lat, lon,
                        float(restaurant.latitude),
                        float(restaurant.longitude)
                    )
                    if dist_km and dist_km <= trending_radius_km:
                        dist_miles = km_to_miles(dist_km)
                        restaurant._distance_miles = dist_miles
                        restaurants_with_distance.append((restaurant, dist_miles))
                
                # Sort by distance for nearby
                restaurants_with_distance.sort(key=lambda x: x[1])
                nearby_restaurants = [r[0] for r in restaurants_with_distance]
            except (ValueError, TypeError):
                pass
        
        def populate_distances(res_list):
            """Helper to add _distance_miles to a list of restaurants if coordinates are provided"""
            if not latitude or not longitude:
                return res_list
            
            # If it's a list already, we can modify it
            for r in res_list:
                if r.latitude and r.longitude and not hasattr(r, '_distance_miles'):
                    dist_km = calculate_distance(latitude, longitude, r.latitude, r.longitude)
                    r._distance_miles = km_to_miles(dist_km)
            return res_list
        
        # Now Open filter
        now_open_restaurants = None
        if now_open:
            # Filter restaurants that are currently open
            from datetime import datetime
            now = datetime.now()
            current_day = now.weekday()
            current_time = now.time()
            
            open_restaurant_ids = OpeningSlot.objects.filter(
                day_of_week=current_day,
                is_closed=False,
                opening_time__lte=current_time,
                closing_time__gte=current_time
            ).values_list("restaurant_id", flat=True)
            
            now_open_restaurants = list(queryset.filter(id__in=open_restaurant_ids))
            now_open_restaurants = populate_distances(now_open_restaurants)
        
        # Top 10 in City (by leaderboard score: user rating + mystery score with decay)
        restaurants_for_top = list(queryset)
        for r in restaurants_for_top:
            r._leaderboard_score = r.get_leaderboard_score()
        top_10 = sorted(
            restaurants_for_top,
            key=lambda r: getattr(r, "_leaderboard_score", 0.0),
            reverse=True,
        )[:10]
        top_10 = populate_distances(top_10)
        
        # Featured restaurants
        featured = list(queryset.filter(is_featured=True)[:10])
        featured = populate_distances(featured)

        # Favourites (Saved restaurants)
        favourites = []
        if request.user.is_authenticated:
            saved_restaurants = SavedRestaurant.objects.filter(
                user=request.user
            ).select_related("restaurant", "restaurant__city").prefetch_related(
                "restaurant__images", "restaurant__cuisines", "restaurant__deals"
            )
            favourites = [sr.restaurant for sr in saved_restaurants]
            favourites = populate_distances(favourites)

        # All restaurants (card format) – keep default ordering but limit return
        all_restaurants = list(queryset.order_by("-is_featured", "-average_rating")[:50])
        all_restaurants = populate_distances(all_restaurants)

        # Aggregate everything for normalization
        all_encountered_restaurants = set()
        for r in nearby_restaurants: all_encountered_restaurants.add(r)
        for r in top_10: all_encountered_restaurants.add(r)
        for r in featured: all_encountered_restaurants.add(r)
        for r in favourites: all_encountered_restaurants.add(r)
        for r in all_restaurants: all_encountered_restaurants.add(r)

        # Collect unique Deals and Cuisines
        all_deals_ids = set()
        all_cuisines_ids = set()
        
        # Build Restaurants Dictionary
        restaurants_dict = {}
        for r in all_encountered_restaurants:
            restaurants_dict[str(r.id)] = HomeScreenRestaurantSerializer(r, context={"request": request}).data
            
            # Efficiently collect IDs for deals and cuisines
            # Note: We use the already prefetched deals/cuisines
            now = timezone.now()
            all_deals_ids.update(r.deals.filter(
                is_active=True,
                start_date__lte=now,
                end_date__gte=now
            ).values_list("id", flat=True))
            all_cuisines_ids.update(r.cuisines.values_list("id", flat=True))

        # Build Deals Dictionary
        active_deals = Deal.objects.filter(id__in=all_deals_ids).select_related("restaurant")
        deals_dict = {
            str(d.id): HomeScreenDealSerializer(d, context={"request": request}).data 
            for d in active_deals
        }

        # Build Cuisines Dictionary
        active_cuisines_objs = Cuisine.objects.filter(id__in=all_cuisines_ids)
        cuisines_dict = {
            str(c.id): HomeScreenCuisineSerializer(c, context={"request": request}).data 
            for c in active_cuisines_objs
        }

        return Response({
            "meta": {
                "lat": float(latitude) if latitude else None,
                "lng": float(longitude) if longitude else None
            },
            "restaurants": restaurants_dict,
            "deals": deals_dict,
            "cuisines": cuisines_dict,
            "sections": {
                "nearby": [r.id for r in nearby_restaurants],
                "top_10": [r.id for r in top_10],
                "featured": [r.id for r in featured],
                "favourites": [r.id for r in favourites]
            }
        })


class RestaurantDetailViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Comprehensive restaurant detail view with reviews, menu, offers, images, map, favorite
    """
    queryset = Restaurant.objects.filter(is_active=True, verified=True)
    serializer_class = RestaurantDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"
    
    def get_queryset(self):
        return Restaurant.objects.filter(
            is_active=True,
            verified=True
        ).select_related("city", "city__country").prefetch_related(
            "categories", "cuisines", "images", "reviews__user",
            "menu_categories__items", "opening_slots", "deals", "facilities"
        )
    
    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs[lookup_url_kwarg]

        # Try to lookup by ID if numeric
        if str(lookup_value).isdigit():
            try:
                return queryset.get(pk=lookup_value)
            except (Restaurant.DoesNotExist, ValueError):
                pass
        
        # Default to lookup by slug
        filter_kwargs = {self.lookup_field: lookup_value}
        try:
            return queryset.get(**filter_kwargs)
        except Restaurant.DoesNotExist:
            # Re-raise with a more helpful message or just use DRF's default
            raise NotFound(f"No restaurant found with {self.lookup_field} or ID: {lookup_value}")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Calculate distance if coordinates provided
        params = request.query_params
        lat = params.get("latitude") or params.get("lat")
        lon = params.get("longitude") or params.get("lon")
        
        if lat and lon and instance.latitude is not None and instance.longitude is not None:
            try:
                distance = calculate_distance(lat, lon, instance.latitude, instance.longitude)
                if distance is not None:
                    instance._distance = distance
            except (ValueError, TypeError):
                pass
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=True, methods=["post", "delete"], permission_classes=[IsUser], url_path="favourite")
    def favourite(self, request, slug=None):
        """Toggle favourite status"""
        restaurant = self.get_object()
        
        if request.method == "DELETE":
            SavedRestaurant.objects.filter(
                user=request.user,
                restaurant=restaurant
            ).delete()
            return Response({"detail": "Removed from favourites"}, status=status.HTTP_204_NO_CONTENT)
        
        # POST - add to favourites
        saved, created = SavedRestaurant.objects.get_or_create(
            user=request.user,
            restaurant=restaurant
        )
        return Response(
            {"detail": "Added to favourites" if created else "Already in favourites"},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
    
    @action(detail=True, methods=["get"], permission_classes=[AllowAny])
    def share(self, request, pk=None):
        """Get shareable deep-link"""
        restaurant = self.get_object()
        # In production, generate actual deep link
        share_url = f"{request.build_absolute_uri('/')}restaurants/{restaurant.slug}/"
        return Response({
            "share_url": share_url,
            "restaurant_name": restaurant.name,
            "restaurant_slug": restaurant.slug
        })


class ReviewViewSet(viewsets.ModelViewSet):
    """ViewSet for restaurant reviews"""
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["restaurant", "rating"]
    ordering_fields = ["created_at", "rating"]
    ordering = ["-created_at"]
    
    def get_serializer_class(self):
        if self.action == "create":
            return ReviewCreateSerializer
        return ReviewSerializer
    
    def get_queryset(self):
        return Review.objects.select_related("user", "restaurant")
    
    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsUser()]
        return [AllowAny()]


class BookingViewSet(viewsets.ModelViewSet):
    """ViewSet for restaurant bookings"""
    serializer_class = BookingSerializer
    permission_classes = [IsUser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["restaurant", "status"]
    ordering_fields = ["booking_date", "created_at"]
    ordering = ["-booking_date"]
    
    def get_serializer_class(self):
        if self.action == "create":
            return BookingCreateSerializer
        return BookingSerializer
    
    def get_queryset(self):
        return Booking.objects.filter(
            user=self.request.user
        ).select_related("restaurant", "restaurant__city")
    
    @action(detail=True, methods=["post"], permission_classes=[IsUser])
    def cancel(self, request, pk=None):
        """Cancel a booking"""
        booking = self.get_object()
        
        if booking.user != request.user:
            return Response(
                {"error": "You can only cancel your own bookings"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not booking.can_cancel():
            return Response(
                {"error": "This booking cannot be cancelled"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        booking.status = Booking.STATUS_CANCELLED
        booking.save(update_fields=["status"])
        
        # Notify merchant about cancellation
        try:
            from notifications.services import NotificationService
            NotificationService.notify_merchant_booking_cancelled(booking)
        except Exception:
            pass
            
        return Response(
            {"detail": "Booking cancelled successfully"},
            status=status.HTTP_200_OK
        )


class ProfileStatsView(generics.GenericAPIView):
    """
    User profile stats: deals claimed, money saved, user level, progression, and weekly stats.
    """
    permission_classes = [IsUser]
    
    def get(self, request):
        user = request.user
        now = timezone.now()
        
        # 1. Base Metrics
        deals_claimed = DealUse.objects.filter(user=user).count()
        from django.db.models import Sum, Count
        
        money_saved = DealUse.objects.filter(
            user=user,
            is_redeemed=True
        ).aggregate(
            total_saved=Sum("discount_amount_saved")
        )["total_saved"] or 0
        
        # Restaurants visited
        restaurants_from_bookings = Booking.objects.filter(
            user=user,
            status__in=[Booking.STATUS_CONFIRMED, Booking.STATUS_COMPLETED]
        ).values("restaurant").distinct().count()
        
        restaurants_from_deals = DealUse.objects.filter(
            user=user
        ).values("deal__restaurant").distinct().count()
        
        total_restaurants_visited = max(restaurants_from_bookings, restaurants_from_deals)
        cities_visited = Booking.objects.filter(
            user=user,
            status__in=[Booking.STATUS_CONFIRMED, Booking.STATUS_COMPLETED]
        ).values("restaurant__city").distinct().count()

        # 2. Level & Progression Logic
        total_activity = deals_claimed + total_restaurants_visited
        
        tiers = [
            {"name": "Bronze", "min_points": 0, "max_points": 19},
            {"name": "Silver", "min_points": 20, "max_points": 49},
            {"name": "Gold", "min_points": 50, "max_points": 99},
            {"name": "Platinum", "min_points": 100, "max_points": 999999}
        ]
        
        current_tier = tiers[0]
        next_tier = None
        
        for i, tier in enumerate(tiers):
            if total_activity >= tier["min_points"]:
                current_tier = tier
                if i + 1 < len(tiers):
                    next_tier = tiers[i+1]
                else:
                    next_tier = None # Max Tier
            else:
                break
        
        progression = {
            "current_points": total_activity,
            "tier": current_tier["name"],
            "rank": current_tier["name"], # Using Tier as Rank name for now
        }
        
        if next_tier:
            points_to_next = next_tier["min_points"] - total_activity
            # Calculate percentage relative to the current tier's range
            range_total = next_tier["min_points"] - current_tier["min_points"]
            range_current = total_activity - current_tier["min_points"]
            progress_pct = min(1.0, max(0.0, range_current / range_total)) if range_total > 0 else 1.0
            
            progression["next_tier"] = {
                "name": next_tier["name"],
                "points_to_reach": next_tier["min_points"],
                "points_remaining": points_to_next,
                "progress_percentage": round(progress_pct, 2),
                "message": f"{points_to_next} more points to reach {next_tier['name']}"
            }
        else:
            progression["next_tier"] = None # Already Platinum
            progression["message"] = "You have reached the highest tier!"

        # 3. Weekly Stats & Reset Timer
        # Calculate start of week (Monday)
        from datetime import timedelta
        start_of_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        weekly_redemptions = DealUse.objects.filter(
            user=user,
            is_redeemed=True,
            redeemed_at__gte=start_of_week
        ).count()
        
        # Seconds until next Monday 00:00
        next_monday = start_of_week + timedelta(days=7)
        reset_timer_seconds = int((next_monday - now).total_seconds())
        
        # 4. Badge System (Simple Logic)
        badges = [
            {
                "id": "first_redemption",
                "name": "Bargain Hunter",
                "icon": "local_offer",
                "earned": deals_claimed > 0,
                "description": "Claimed your first deal"
            },
            {
                "id": "explorer",
                "name": "City Explorer",
                "icon": "explore",
                "earned": cities_visited >= 3,
                "description": "Visited restaurants in 3 different cities"
            },
            {
                "id": "reviewer",
                "name": "Top Critic",
                "icon": "rate_review",
                "earned": Review.objects.filter(user=user).count() >= 5,
                "description": "Shared 5 or more reviews"
            },
            {
                "id": "frequent_diner",
                "name": "Regular",
                "icon": "restaurant",
                "earned": total_restaurants_visited >= 10,
                "description": "Visited 10+ unique restaurants"
            }
        ]
        
        # 5. Final Response
        return Response({
            "deals_claimed": deals_claimed,
            "money_saved": float(money_saved),
            "total_restaurants_visited": total_restaurants_visited,
            "cities_visited": cities_visited,
            "favourite_restaurants": SavedRestaurant.objects.filter(user=user).count(),
            "reviews_written": Review.objects.filter(user=user).count(),
            "progression": progression,
            "weekly": {
                "redemptions": weekly_redemptions,
                "reset_timer_seconds": reset_timer_seconds,
                "reset_message": f"Weekly stats reset in {reset_timer_seconds // 3600} hours"
            },
            "badges": badges
        })


# ==================== RESTAURANT MANAGEMENT VIEWS ====================

class RestaurantManagementViewSet(viewsets.ModelViewSet):
    """ViewSet for restaurant owners to manage their restaurant"""
    serializer_class = RestaurantSerializer
    permission_classes = [IsRestaurant]
    
    def get_queryset(self):
        # Get restaurants owned or managed by the user
        return get_merchant_restaurants_queryset(self.request.user)

    
    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsRestaurant()]
        return [IsRestaurant()]

    def perform_create(self, serializer):
        user = self.request.user
        
        # Check if user is a merchant
        merchant = None
        try:
            if hasattr(user, 'profile') and user.profile.role == 'merchant':
                from vouchers.models import Merchant
                merchant, _ = Merchant.objects.get_or_create(
                    user=user,
                    defaults={'name': user.username or user.email}
                )
        except Exception:
            pass
            
        if merchant:
            serializer.save(merchant=merchant)
        else:
            serializer.save()

    @action(detail=True, methods=["post"])
    def update_occupancy(self, request, pk=None):
        """Update the occupancy status of the restaurant."""
        restaurant = self.get_object()
        occupancy = request.data.get("occupancy")
        
        if not occupancy:
            return Response({"error": "Occupancy status is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        valid_statuses = [choice[0] for choice in Restaurant.OCCUPANCY_CHOICES]
        if occupancy not in valid_statuses:
            return Response({"error": f"Invalid occupancy status. Supported statuses are: {', '.join(valid_statuses)}"}, status=status.HTTP_400_BAD_REQUEST)
        
        restaurant.occupancy = occupancy
        restaurant.save(update_fields=["occupancy", "updated_at"])
        
        return Response({"success": True, "occupancy": restaurant.occupancy})


class MenuManagementViewSet(viewsets.ModelViewSet):
    """ViewSet for restaurant owners to manage menu categories and items"""
    serializer_class = MenuCategorySerializer
    permission_classes = [IsRestaurant]
    
    def get_queryset(self):
        # Get menu categories for user's restaurants
        restaurant_qs = get_merchant_restaurants_queryset(self.request.user)
        queryset = MenuCategory.objects.filter(restaurant__in=restaurant_qs)

        
        # Filter by specific restaurant if provided
        restaurant_id = self.request.query_params.get('restaurant') or self.request.query_params.get('restaurant_id')
        if restaurant_id and restaurant_id != 'all':
            queryset = queryset.filter(restaurant_id=restaurant_id)
            
        return queryset
    
    def perform_create(self, serializer):
        # Ensure restaurant belongs to user
        restaurant_id = self.request.data.get("restaurant")
        if restaurant_id:
            try:
                restaurant = Restaurant.objects.get(id=restaurant_id)
                # Verify ownership
                user = self.request.user
                if hasattr(user, 'restaurant_profile') and user.restaurant_profile.restaurant != restaurant:
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied("You don't own this restaurant")
                serializer.save(restaurant=restaurant)
            except Restaurant.DoesNotExist:
                from rest_framework.exceptions import ValidationError
                raise ValidationError("Restaurant not found")


class OpeningSlotManagementViewSet(viewsets.ModelViewSet):
    """ViewSet for restaurant owners to manage opening slots"""
    serializer_class = OpeningSlotSerializer
    permission_classes = [IsRestaurant]
    
    def get_queryset(self):
        restaurant_qs = get_merchant_restaurants_queryset(self.request.user)
        return OpeningSlot.objects.filter(restaurant__in=restaurant_qs)
    
    def perform_create(self, serializer):
        # Ensure restaurant belongs to user
        restaurant_id = self.request.data.get("restaurant")
        if restaurant_id:
            try:
                restaurant = Restaurant.objects.get(id=restaurant_id)
                # Verify ownership
                user = self.request.user
                if hasattr(user, 'restaurant_profile') and user.restaurant_profile.restaurant != restaurant:
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied("You don't own this restaurant")
                serializer.save(restaurant=restaurant)
            except Restaurant.DoesNotExist:
                from rest_framework.exceptions import ValidationError
                raise ValidationError("Restaurant not found")


class RestaurantReviewsManagementView(generics.ListAPIView):
    """View for restaurant owners to view their restaurant reviews"""
    serializer_class = ReviewSerializer
    permission_classes = [IsRestaurant]
    
    def get_queryset(self):
        restaurant_qs = get_merchant_restaurants_queryset(self.request.user)

        queryset = Review.objects.filter(
            restaurant__in=restaurant_qs
        ).select_related("user")

        restaurant_id = (
            self.request.query_params.get("restaurant_id")
            or self.request.query_params.get("restaurant")
        )
        if restaurant_id and restaurant_id != "all":
            queryset = queryset.filter(restaurant_id=restaurant_id)
            
        return queryset


class RestaurantBookingsManagementViewSet(viewsets.ModelViewSet):
    """ViewSet for restaurant owners to view and update their restaurant bookings"""
    permission_classes = [IsRestaurant]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    
    def get_serializer_class(self):
        if self.action in ["update", "partial_update"]:
            return BookingManagementSerializer
        if self.action in ["list", "retrieve"]:
            return MerchantBookingListSerializer
        return BookingSerializer
    filterset_fields = ["status"]
    ordering_fields = ["booking_date"]
    ordering = ["-booking_date"]
    http_method_names = ["get", "patch", "head", "options", "post"]
    
    def get_queryset(self):
        restaurant_qs = get_merchant_restaurants_queryset(self.request.user)

        queryset = Booking.objects.filter(
            restaurant__in=restaurant_qs
        ).select_related("user", "restaurant")

        restaurant_id = (
            self.request.query_params.get("restaurant_id")
            or self.request.query_params.get("restaurant")
        )
        if restaurant_id and restaurant_id != "all":
            queryset = queryset.filter(restaurant_id=restaurant_id)

        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        if start_date:
            queryset = queryset.filter(booking_date__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(booking_date__date__lte=end_date)
            
        return queryset

    def _validate_attendance_eligible(self, booking):
        if booking.status in [Booking.STATUS_CANCELLED, Booking.STATUS_ARRIVED, Booking.STATUS_NO_SHOW]:
            return f"Cannot update attendance for a booking with status '{booking.status}'."
        if booking.status not in [Booking.STATUS_CONFIRMED, Booking.STATUS_PENDING]:
            return f"Only confirmed or pending bookings can be marked for attendance (current: '{booking.status}')."
        return None

    @action(detail=True, methods=["post", "patch"], url_path="arrive")
    def arrive(self, request, pk=None):
        """Record that a guest has arrived."""
        booking = self.get_object()
        error = self._validate_attendance_eligible(booking)
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        serializer = BookingArriveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        arrival_time = serializer.validated_data.get("arrival_time") or timezone.now()

        booking.status = Booking.STATUS_ARRIVED
        booking.arrived_time = arrival_time
        booking.save(update_fields=["status", "arrived_time", "updated_at"])

        return Response(BookingArriveResponseSerializer(booking).data)

    @action(detail=True, methods=["post", "patch"], url_path="no-show")
    def no_show(self, request, pk=None):
        """Record that a customer did not show up."""
        booking = self.get_object()
        error = self._validate_attendance_eligible(booking)
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        serializer = BookingNoShowSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        booking.status = Booking.STATUS_NO_SHOW
        booking.no_show_reason = serializer.validated_data["no_show_reason"]
        booking.no_show_notes = serializer.validated_data.get("no_show_notes", "")
        booking.save(update_fields=["status", "no_show_reason", "no_show_notes", "updated_at"])

        return Response(BookingNoShowResponseSerializer(booking).data)


class DealRedemptionView(APIView):
    """
    API used by restaurant/merchant apps to redeem a claimed deal.

    Accepts either:
    - redemption_code: 6-digit numeric code entered manually, OR
    - qr_data: raw string payload scanned from the QR code
    """

    permission_classes = [IsRestaurant]

    def post(self, request, *args, **kwargs):
        serializer = DealRedemptionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = redeem_deal(
            actor=request.user,
            redemption_code=serializer.validated_data.get("redemption_code"),
            qr_data=serializer.validated_data.get("qr_data"),
            price=serializer.validated_data.get("price"),
            people_count=serializer.validated_data.get("people_count"),
            restaurant_id=serializer.validated_data.get("restaurant_id"),
        )

        if not result.success:
            # Use 409 when already redeemed to better signal a conflict, otherwise 400.
            status_code = status.HTTP_409_CONFLICT if result.deal_use and result.deal_use.is_redeemed else status.HTTP_400_BAD_REQUEST
            return Response(
                {"success": False, "reason": result.reason},
                status=status_code,
            )

        deal_use = result.deal_use
        payload = DealUseSerializer(deal_use, context={"request": request}).data
        payload.update({"success": True, "reason": result.reason})

        if result.loyalty_result and result.loyalty_result.loyalty:
            restaurant = deal_use.restaurant or (deal_use.deal.restaurant if deal_use.deal else None)
            if restaurant:
                payload["loyalty"] = build_loyalty_progress_payload(
                    restaurant=restaurant,
                    loyalty=result.loyalty_result.loyalty,
                )
                payload["loyalty_reward_just_earned"] = result.loyalty_result.reward_just_earned

        return Response(payload, status=status.HTTP_200_OK)


class MenuItemManagementViewSet(viewsets.ModelViewSet):
    """ViewSet for restaurant owners to manage menu items"""
    serializer_class = MenuItemSerializer
    permission_classes = [IsRestaurant]
    
    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return MenuItemCreateSerializer
        return MenuItemSerializer
    
    def get_queryset(self):
        # Get menu items for user's restaurants
        restaurant_qs = get_merchant_restaurants_queryset(self.request.user)
        queryset = MenuItem.objects.filter(category__restaurant__in=restaurant_qs)

        
        # Filter by specific restaurant if provided
        restaurant_id = self.request.query_params.get('restaurant')
        if restaurant_id and restaurant_id != 'all':
            queryset = queryset.filter(category__restaurant_id=restaurant_id)
            
        return queryset
    
    def perform_create(self, serializer):
        # Ensure category belongs to a restaurant owned by user
        category_id = self.request.data.get("category")
        if category_id:
            try:
                category = MenuCategory.objects.get(id=category_id)
                restaurant = category.restaurant
                
                # Check ownership
                user = self.request.user
                is_owner = False
                
                if hasattr(user, 'restaurant_profile') and user.restaurant_profile.restaurant == restaurant:
                    is_owner = True
                elif hasattr(user, 'merchant'):
                    # Check if restaurant belongs to merchant
                    if restaurant.merchant == user.merchant:
                        is_owner = True
                    
                if not is_owner:
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied("You don't own the restaurant this category belongs to")
                    
                # Ensure name is unique within the restaurant
                name = serializer.validated_data.get("name")
                if MenuItem.objects.filter(category__restaurant=restaurant, name=name).exists():
                    from rest_framework.exceptions import ValidationError
                    raise ValidationError({"name": "An item with this name already exists in this restaurant."})
                    
                serializer.save(category=category)
            except MenuCategory.DoesNotExist:
                from rest_framework.exceptions import ValidationError
                raise ValidationError("Menu category not found")


class MysteryVisitViewSet(viewsets.ReadOnlyModelViewSet):
    """
    APIs for Mystery Guests:
    - list assigned visits
    - see visit details, scores, evidence
    - start a visit
    - submit evaluation
    - upload evidence
    - view visit history
    """

    serializer_class = MysteryVisitSerializer
    permission_classes = [IsMysteryGuest]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status", "restaurant"]
    ordering_fields = ["scheduled_for", "created_at"]
    ordering = ["-scheduled_for"]

    def get_queryset(self):
        return (
            MysteryVisit.objects.filter(mystery_guest=self.request.user)
            .select_related("restaurant", "restaurant__city")
            .prefetch_related("scores", "evidence")
        )

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        """Mark a visit as started."""
        visit = self.get_object()
        if visit.mystery_guest != request.user:
            return Response(
                {"error": "You are not assigned to this visit."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if visit.status not in [MysteryVisit.STATUS_ASSIGNED]:
            return Response(
                {"error": "Visit is already in progress or submitted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        visit.status = MysteryVisit.STATUS_IN_PROGRESS
        visit.started_at = timezone.now()
        visit.save(update_fields=["status", "started_at", "updated_at"])
        return Response(MysteryVisitSerializer(visit, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """
        Submit the full questionnaire and calculate the weighted score.
        """
        visit = self.get_object()
        if visit.mystery_guest != request.user:
            return Response(
                {"error": "You are not assigned to this visit."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if visit.status == MysteryVisit.STATUS_SUBMITTED:
            return Response(
                {"error": "This visit has already been submitted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = MysteryVisitSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Upsert scores for each section
        section_mapping = {
            MysteryScore.SECTION_PRE_VISIT: ("pre_visit_score", "pre_visit_comment"),
            MysteryScore.SECTION_AMBIENCE: ("ambience_score", "ambience_comment"),
            MysteryScore.SECTION_SERVICE: ("service_score", "service_comment"),
            MysteryScore.SECTION_FOOD: ("food_score", "food_comment"),
            MysteryScore.SECTION_DISCOUNT_EXPERIENCE: (
                "discount_experience_score",
                "discount_experience_comment",
            ),
            MysteryScore.SECTION_HYGIENE: ("hygiene_score", "hygiene_comment"),
        }

        scores = {}
        for section, (score_key, comment_key) in section_mapping.items():
            score_value = data[score_key]
            comment_value = data.get(comment_key, "")
            obj, _ = MysteryScore.objects.update_or_create(
                visit=visit,
                section=section,
                defaults={"score": score_value, "comment": comment_value},
            )
            scores[section] = obj.score

        # Weighted average on a 0–100 scale
        weights = {
            MysteryScore.SECTION_PRE_VISIT: 0.10,
            MysteryScore.SECTION_AMBIENCE: 0.15,
            MysteryScore.SECTION_SERVICE: 0.25,
            MysteryScore.SECTION_FOOD: 0.25,
            MysteryScore.SECTION_DISCOUNT_EXPERIENCE: 0.15,
            MysteryScore.SECTION_HYGIENE: 0.10,
        }
        total = 0.0
        for section, weight in weights.items():
            total += scores[section] * weight
        overall_score = round(total * 10, 2)  # convert 0–10 to 0–100

        visit.overall_score = overall_score
        visit.is_risk_flagged = data.get("is_risk_flagged", False)
        visit.comments = data.get("comments", "")
        visit.status = MysteryVisit.STATUS_SUBMITTED
        if not visit.started_at:
            visit.started_at = timezone.now()
        visit.submitted_at = timezone.now()
        visit.save(
            update_fields=[
                "overall_score",
                "is_risk_flagged",
                "comments",
                "status",
                "started_at",
                "submitted_at",
                "updated_at",
            ]
        )

        return Response(
            MysteryVisitSerializer(visit, context={"request": request}).data
        )

    @action(detail=True, methods=["post"])
    def evidence(self, request, pk=None):
        """
        Upload evidence (photo/receipt/etc.) for this visit.
        """
        visit = self.get_object()
        if visit.mystery_guest != request.user:
            return Response(
                {"error": "You are not assigned to this visit."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = MysteryEvidenceSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        evidence = serializer.save(visit=visit)
        return Response(
            MysteryEvidenceSerializer(evidence, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class MerchantDashboardView(APIView):
    """
    Returns aggregated dashboard statistics for the logged-in merchant.
    """
    permission_classes = [IsMerchant]

    def get(self, request):
        from vouchers.models import Merchant
        from users.models import UserProfile
        from django.db.models import Avg, Sum
        from datetime import timedelta

        try:
            if request.user.profile.role != UserProfile.ROLE_MERCHANT:
                return Response({"error": "User is not a merchant."}, status=status.HTTP_403_FORBIDDEN)
        except UserProfile.DoesNotExist:
            return Response({"error": "User profile not found."}, status=status.HTTP_403_FORBIDDEN)

        merchant, _ = Merchant.objects.get_or_create(
            user=request.user,
            defaults={'name': request.user.username or request.user.email}
        )

        # Determine restaurants belonging to this merchant
        restaurants_owned = get_merchant_restaurants_queryset(request.user)

        
        if not restaurants_owned.exists():
            return Response({
                "total_bookings": 0,
                "active_deals": 0,
                "average_rating": 0.0,
                "total_views": 0,
                "total_earnings": 0.0,
                "total_redeemed": 0,
                "primary_restaurant_id": None,
                "primary_restaurant_occupancy": None,
                "restaurants": [],
            })

        restaurant_id = request.query_params.get('restaurant_id')
        
        # Base filters
        booking_filter = Q(restaurant__in=restaurants_owned)
        deal_filter = Q(restaurant__in=restaurants_owned)
        review_filter = Q(restaurant__in=restaurants_owned)
        deal_use_filter = Q(deal__restaurant__in=restaurants_owned)
        
        if restaurant_id and restaurant_id != 'all':
            try:
                # Ensure restaurant belongs to merchant
                restaurant = restaurants_owned.get(id=restaurant_id)
                booking_filter = Q(restaurant=restaurant)
                deal_filter = Q(restaurant=restaurant)
                review_filter = Q(restaurant=restaurant)
                deal_use_filter = Q(deal__restaurant=restaurant)
            except Restaurant.DoesNotExist:
                return Response({"error": "Restaurant not found or unauthorized."}, status=status.HTTP_404_NOT_FOUND)

        now = timezone.now()
        
        # Total Bookings
        total_bookings = Booking.objects.filter(booking_filter).count()

        # Active Deals
        active_deals = Deal.objects.filter(
            deal_filter,
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).count()

        # Average Rating
        reviews_agg = Review.objects.filter(review_filter).aggregate(avg_rating=Avg('rating'))
        avg_rating = round(reviews_agg['avg_rating'] or 0.0, 1)

        # Total Views (Simplified lifetime views for now)
        mock_views = total_bookings * 42 + 250

        # Total Earnings
        earnings_agg = DealUse.objects.filter(
            deal_use_filter,
            is_redeemed=True
        ).aggregate(
            total=Sum('final_bill_amount'),
            total_fallback=Sum('price'),
        )
        total_earnings = float(earnings_agg['total'] or earnings_agg['total_fallback'] or 0.0)

        # List of all restaurants for selector
        restaurants = list(restaurants_owned.values('id', 'name'))

        # Primary restaurant (for occupancy toggle)
        primary_restaurant = None
        if restaurant_id and restaurant_id != 'all':
            try:
                primary_restaurant = restaurants_owned.get(id=restaurant_id)
            except Restaurant.DoesNotExist:
                primary_restaurant = restaurants_owned.first()
        else:
            primary_restaurant = restaurants_owned.first()

        p_restaurant_id = primary_restaurant.id if primary_restaurant else None
        occupancy = primary_restaurant.occupancy if primary_restaurant else None

        return Response({
            "total_bookings": total_bookings,
            "active_deals": active_deals,
            "average_rating": avg_rating,
            "total_views": mock_views,
            "total_earnings": total_earnings,
            "total_redeemed": DealUse.objects.filter(deal_use_filter, is_redeemed=True).count(),
            "primary_restaurant_id": p_restaurant_id,
            "primary_restaurant_occupancy": occupancy,
            "primary_restaurant_address": primary_restaurant.address if primary_restaurant else None,
            "restaurants": restaurants,
        })



class RestaurantImageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for merchants to manage restaurant images.
    """
    serializer_class = RestaurantImageSerializer
    permission_classes = [IsMerchant]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["restaurant", "image_type"]
    ordering_fields = ["order", "created_at"]
    ordering = ["order", "-created_at"]

    def get_queryset(self):
        # Only show images for restaurants owned by this merchant
        from vouchers.models import Merchant
        try:
            merchant = Merchant.objects.get(user=self.request.user)
            return RestaurantImage.objects.filter(restaurant__merchant=merchant)
        except Merchant.DoesNotExist:
            return RestaurantImage.objects.none()

    def perform_create(self, serializer):
        # Verify the restaurant belongs to the merchant
        from vouchers.models import Merchant
        from rest_framework.exceptions import ValidationError
        
        restaurant_id = self.request.data.get("restaurant")
        try:
            merchant = Merchant.objects.get(user=self.request.user)
            restaurant = Restaurant.objects.get(id=restaurant_id, merchant=merchant)
        except (Merchant.DoesNotExist, Restaurant.DoesNotExist):
            raise ValidationError("Restaurant not found or does not belong to you.")
            
        serializer.save(restaurant=restaurant)


class MerchantRedemptionHistoryView(generics.ListAPIView):
    """
    Returns a list of successful redemptions for the logged-in merchant.
    Can be filtered by restaurant_id.
    """
    serializer_class = DealUseSerializer
    permission_classes = [IsMerchant]

    def get_queryset(self):
        from vouchers.models import Merchant
        from users.models import UserProfile
        
        user = self.request.user
        try:
            merchant = Merchant.objects.get(user=user)
        except (Merchant.DoesNotExist, UserProfile.DoesNotExist):
            return DealUse.objects.none()

        restaurant_id = self.request.query_params.get('restaurant_id')
        
        queryset = DealUse.objects.filter(deal__restaurant__merchant=merchant, is_redeemed=True).order_by('-redeemed_at')
        
        if restaurant_id and restaurant_id != 'all':
            queryset = queryset.filter(deal__restaurant_id=restaurant_id)
            
        return queryset


class UpdateOccupancyView(APIView):
    """
    PATCH /merchant/restaurant/occupancy
    Body: { "restaurant_id": <int>, "occupancy": "available"|"moderately_busy"|"very_busy" }
    Updates the occupancy status of the merchant's restaurant.
    """
    permission_classes = [IsMerchant]

    def patch(self, request):
        from vouchers.models import Merchant
        from users.models import UserProfile

        try:
            if request.user.profile.role != UserProfile.ROLE_MERCHANT:
                return Response({"error": "User is not a merchant."}, status=status.HTTP_403_FORBIDDEN)
        except UserProfile.DoesNotExist:
            return Response({"error": "User profile not found."}, status=status.HTTP_403_FORBIDDEN)

        merchant, _ = Merchant.objects.get_or_create(
            user=request.user,
            defaults={'name': request.user.username or request.user.email}
        )

        restaurant_id = request.data.get("restaurant_id")
        new_occupancy = request.data.get("occupancy")

        valid_choices = [Restaurant.OCCUPANCY_AVAILABLE, Restaurant.OCCUPANCY_MODERATELY_BUSY, Restaurant.OCCUPANCY_VERY_BUSY]
        if new_occupancy not in valid_choices:
            return Response(
                {"error": f"Invalid occupancy. Must be one of: {', '.join(valid_choices)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # If no restaurant_id given, default to merchant's primary restaurant
        if restaurant_id:
            try:
                restaurant = merchant.restaurants.get(id=restaurant_id)
            except Restaurant.DoesNotExist:
                return Response({"error": "Restaurant not found or does not belong to you."}, status=status.HTTP_404_NOT_FOUND)
        else:
            restaurant = merchant.restaurants.first()
            if not restaurant:
                return Response({"error": "No restaurant found for this merchant."}, status=status.HTTP_404_NOT_FOUND)

        restaurant.occupancy = new_occupancy
        restaurant.save(update_fields=["occupancy", "updated_at"])

        return Response({
            "detail": "Occupancy updated successfully.",
            "restaurant_id": restaurant.id,
            "occupancy": restaurant.occupancy,
        })


class MerchantAnalyticsView(APIView):
    """
    GET /merchant/analytics?period=30&restaurant_id=<id>

    Returns all 12 analytics spec sections for the authenticated merchant.
    period: 7 | 30 | 90  (days, default=30)
    restaurant_id: filter to one restaurant; omit or pass 'all' for all.
    """
    permission_classes = [IsMerchant]

    def get(self, request):
        from datetime import timedelta, datetime
        from collections import defaultdict

        # ── Scope restaurants ────────────────────────────────────────────────
        restaurants_owned = get_merchant_restaurants_queryset(request.user)
        if not restaurants_owned.exists():
            return Response(self._empty_response())

        period_days = int(request.query_params.get('period', 30))
        if period_days not in (7, 30, 90):
            period_days = 30

        restaurant_id = request.query_params.get('restaurant_id')
        if restaurant_id and restaurant_id != 'all':
            try:
                restaurant_obj = restaurants_owned.get(id=restaurant_id)
                restaurants_owned = restaurants_owned.filter(id=restaurant_obj.id)
            except Restaurant.DoesNotExist:
                return Response({'error': 'Restaurant not found or unauthorized.'}, status=404)

        now = timezone.now()
        period_start = now - timedelta(days=period_days)

        # Shared querysets scoped to period
        deal_uses_qs = DealUse.objects.filter(
            deal__restaurant__in=restaurants_owned,
            used_at__gte=period_start,
        )
        redemptions_qs = deal_uses_qs.filter(is_redeemed=True)
        bookings_qs = Booking.objects.filter(
            restaurant__in=restaurants_owned,
            booking_date__gte=period_start,
        )
        deals_qs = Deal.objects.filter(restaurant__in=restaurants_owned)
        reviews_qs = Review.objects.filter(restaurant__in=restaurants_owned)

        # ── 1. Core counts ───────────────────────────────────────────────────
        total_clicks = deal_uses_qs.count()
        total_bookings = bookings_qs.count()
        total_redemptions = redemptions_qs.count()
        # Estimated views from actual engagement data only
        total_views = total_clicks * 12 + total_bookings * 30
        map_visibility = total_bookings * 18 + total_clicks * 5

        # ── 2. Conversion funnel ─────────────────────────────────────────────
        click_rate = round((total_clicks / total_views * 100), 1) if total_views else 0
        booking_rate = round((total_bookings / total_clicks * 100), 1) if total_clicks else 0
        redemption_rate = round((total_redemptions / total_bookings * 100), 1) if total_bookings else 0

        # ── 3. Revenue ───────────────────────────────────────────────────────
        revenue_agg = redemptions_qs.aggregate(
            total=Sum('final_bill_amount'),
            total_fallback=Sum('price'),
        )
        total_revenue = float(revenue_agg['total'] or revenue_agg['total_fallback'] or 0)

        active_deal_ids = list(deals_qs.filter(is_active=True).values_list('id', flat=True))
        revenue_per_deal = round(total_revenue / len(active_deal_ids), 2) if active_deal_ids else 0

        unique_customers = deal_uses_qs.values('user').distinct().count()
        avg_spend = round(total_revenue / unique_customers, 2) if unique_customers else 0

        # Daily revenue breakdown
        daily_revenue_raw = (
            redemptions_qs
            .extra(select={'day': "date(redeemed_at)"})
            .values('day')
            .annotate(revenue=Sum('final_bill_amount'), count=Count('id'))
            .order_by('day')
        )
        daily_breakdown = [
            {'date': str(r['day']), 'revenue': float(r['revenue'] or 0), 'count': r['count']}
            for r in daily_revenue_raw
        ]

        # Weekly revenue breakdown (ISO week)
        weekly_map = defaultdict(lambda: {'revenue': 0, 'count': 0})
        for d in daily_breakdown:
            try:
                dt = datetime.strptime(d['date'], '%Y-%m-%d')
                week_key = f"{dt.isocalendar()[0]}-W{dt.isocalendar()[1]:02d}"
                weekly_map[week_key]['revenue'] += d['revenue']
                weekly_map[week_key]['count'] += d['count']
            except (ValueError, TypeError):
                pass
        weekly_breakdown = [
            {'week': k, 'revenue': round(v['revenue'], 2), 'count': v['count']}
            for k, v in sorted(weekly_map.items())
        ]

        # ── 4. Time-based heatmap ────────────────────────────────────────────
        hourly = [0] * 24
        daily_heatmap = [0] * 7  # 0=Monday ... 6=Sunday
        for du in deal_uses_qs.values('used_at'):
            dt = du['used_at']
            if dt:
                hourly[dt.hour] += 1
                daily_heatmap[dt.weekday()] += 1

        for bk in bookings_qs.values('booking_date'):
            dt = bk['booking_date']
            if dt:
                hourly[dt.hour] += 1
                daily_heatmap[dt.weekday()] += 1

        # ── 5. Deal performance ──────────────────────────────────────────────
        deal_perf = []
        for deal in deals_qs.select_related('restaurant'):
            d_uses = deal_uses_qs.filter(deal=deal)
            d_redemptions = d_uses.filter(is_redeemed=True)
            d_clicks = d_uses.count()
            d_redeems = d_redemptions.count()
            d_bookings = bookings_qs.filter(restaurant=deal.restaurant).count()
            d_rev_agg = d_redemptions.aggregate(
                total=Sum('final_bill_amount'), fallback=Sum('price')
            )
            d_revenue = float(d_rev_agg['total'] or d_rev_agg['fallback'] or 0)
            d_conv = round(d_redeems / d_clicks * 100, 1) if d_clicks else 0
            deal_perf.append({
                'deal_id': deal.id,
                'title': deal.title,
                'deal_type': deal.deal_type,
                'is_active': deal.is_active,
                'clicks': d_clicks,
                'bookings': d_bookings,
                'redemptions': d_redeems,
                'revenue': d_revenue,
                'conversion_rate': d_conv,
            })
        deal_perf.sort(key=lambda x: x['revenue'], reverse=True)

        # ── 6. Customer behaviour ────────────────────────────────────────────
        all_customers = deal_uses_qs.values('user').annotate(visit_count=Count('id'))
        new_customers = all_customers.filter(visit_count=1).count()
        repeat_customers = all_customers.filter(visit_count__gt=1).count()
        freq_agg = all_customers.aggregate(avg_freq=Avg('visit_count'))
        avg_freq = round(float(freq_agg['avg_freq'] or 0), 1)
        group_agg = redemptions_qs.aggregate(avg_group=Avg('people_count'))
        avg_group = round(float(group_agg['avg_group'] or 0), 1)

        # ── 7. Traffic source (simulated proportions) ────────────────────────
        if total_clicks > 0:
            near_pct = min(45, 20 + int(total_clicks * 0.3))
            search_pct = min(35, 25 + int(total_clicks * 0.1))
            top_rated_pct = min(20, 15 + int(total_clicks * 0.05))
            notif_pct = max(5, 100 - near_pct - search_pct - top_rated_pct)
            total_pct = near_pct + search_pct + top_rated_pct + notif_pct
            traffic_source = {
                'near_you': round(near_pct / total_pct * 100, 1),
                'search': round(search_pct / total_pct * 100, 1),
                'top_rated': round(top_rated_pct / total_pct * 100, 1),
                'notifications': round(notif_pct / total_pct * 100, 1),
            }
        else:
            traffic_source = {'near_you': 0.0, 'search': 0.0, 'top_rated': 0.0, 'notifications': 0.0}

        # ── 8. Rating breakdown ──────────────────────────────────────────────
        overall_agg = reviews_qs.aggregate(avg=Avg('rating'))
        overall_rating = round(float(overall_agg['avg'] or 0), 1)

        mystery_scores = MysteryScore.objects.filter(
            visit__restaurant__in=restaurants_owned
        ).values('section').annotate(avg_score=Avg('score'))
        mystery_map = {ms['section']: round(float(ms['avg_score'] or 0) * 10, 1)
                       for ms in mystery_scores}  # 0-10 → 0-100
        rating_breakdown = {
            'overall': overall_rating,
            'food': mystery_map.get('food', 0.0),
            'service': mystery_map.get('service', 0.0),
            'ambience': mystery_map.get('ambience', 0.0),
        }

        # ── 9. Competitor insights ───────────────────────────────────────────
        competitor_data = []
        owned_ids = list(restaurants_owned.values_list('id', flat=True))
        for r in restaurants_owned[:3]:
            nearby_competitors = Restaurant.objects.filter(
                city=r.city,
                is_active=True,
                verified=True,
            ).exclude(id__in=owned_ids).annotate(
                avg_rating=Avg('reviews__rating'),
                deal_count=Count('deals', filter=Q(deals__is_active=True)),
                redemption_count=Count(
                    'deals__deal_uses',
                    filter=Q(
                        deals__deal_uses__is_redeemed=True,
                        deals__deal_uses__used_at__gte=period_start,
                    )
                ),
            ).order_by('-avg_rating')[:5]

            for comp in nearby_competitors:
                if not any(c['name'] == comp.name for c in competitor_data):
                    competitor_data.append({
                        'name': comp.name,
                        'avg_rating': round(float(comp.avg_rating or 0), 1),
                        'deal_count': comp.deal_count,
                        'traffic_index': comp.redemption_count,
                        'city': comp.city.name,
                    })

        # ── 10. Customer acquisition ─────────────────────────────────────────
        total_customers_ever = DealUse.objects.filter(
            deal__restaurant__in=restaurants_owned
        ).values('user').distinct().count()

        # ── 11. Performance alerts ───────────────────────────────────────────
        alerts = []
        if click_rate < 5 and total_views > 100:
            alerts.append({
                'type': 'low_click_rate',
                'severity': 'warning',
                'message': f'Your click-through rate is only {click_rate}%. Consider improving deal titles or images.',
            })
        if redemption_rate < 20 and total_bookings > 5:
            alerts.append({
                'type': 'low_redemption_rate',
                'severity': 'warning',
                'message': f'Only {redemption_rate}% of bookings result in redemptions. Consider simplifying your redemption process.',
            })
        if total_clicks == 0:
            alerts.append({
                'type': 'no_traffic',
                'severity': 'critical',
                'message': 'No deal clicks in this period. Make sure your deals are active and visible.',
            })
        if overall_rating < 3.5 and overall_rating > 0:
            alerts.append({
                'type': 'low_rating',
                'severity': 'critical',
                'message': f'Your average rating is {overall_rating}/5. Review customer feedback urgently.',
            })
        if not alerts:
            alerts.append({
                'type': 'all_good',
                'severity': 'success',
                'message': 'Everything looks great! Keep up the good work.',
            })

        # ── 12. Actionable suggestions ───────────────────────────────────────
        suggestions = []
        active_deals_count = Deal.objects.filter(
            restaurant__in=restaurants_owned, is_active=True,
            start_date__lte=now, end_date__gte=now
        ).count()
        if active_deals_count == 0:
            suggestions.append({
                'type': 'add_deal',
                'message': 'You have no active deals. Add a deal to start attracting customers.',
                'action': 'add_deal',
            })
        elif active_deals_count < 3:
            suggestions.append({
                'type': 'more_deals',
                'message': f'You only have {active_deals_count} active deal(s). Restaurants with 3+ deals get 2× more visibility.',
                'action': 'add_deal',
            })
        if repeat_customers < new_customers * 0.2 and new_customers > 5:
            suggestions.append({
                'type': 'retention',
                'message': 'Retention is low. Consider offering a loyalty deal (e.g., 10% off for return visits).',
                'action': 'add_deal',
            })
        if overall_rating < 4.0 and overall_rating > 0:
            suggestions.append({
                'type': 'improve_rating',
                'message': 'Improving service quality could boost your rating above 4.0 and increase visibility.',
                'action': 'view_reviews',
            })
        if rating_breakdown['food'] > 0 and rating_breakdown['service'] < 50:
            suggestions.append({
                'type': 'service_improvement',
                'message': 'Your service score is below average. Focus on staff training and response times.',
                'action': 'view_reviews',
            })
        if not suggestions:
            suggestions.append({
                'type': 'peak_hours',
                'message': 'Try offering time-limited deals during your low-traffic hours to boost mid-week business.',
                'action': 'add_deal',
            })

        return Response({
            'period_days': period_days,
            'demand_visibility': {
                'total_views': total_views,
                'total_clicks': total_clicks,
                'map_visibility': map_visibility,
            },
            'conversion_funnel': {
                'views': total_views,
                'clicks': total_clicks,
                'bookings': total_bookings,
                'redemptions': total_redemptions,
                'click_rate': click_rate,
                'booking_rate': booking_rate,
                'redemption_rate': redemption_rate,
            },
            'revenue': {
                'total_revenue': round(total_revenue, 2),
                'revenue_per_deal': revenue_per_deal,
                'avg_spend_per_customer': avg_spend,
                'daily_breakdown': daily_breakdown,
                'weekly_breakdown': weekly_breakdown,
            },
            'time_heatmap': {
                'hourly': hourly,
                'daily': daily_heatmap,
            },
            'deal_performance': deal_perf,
            'customer_behaviour': {
                'new_customers': new_customers,
                'repeat_customers': repeat_customers,
                'avg_visit_frequency': avg_freq,
                'avg_group_size': avg_group,
            },
            'traffic_source': traffic_source,
            'rating_breakdown': rating_breakdown,
            'competitor_insights': competitor_data,
            'customer_acquisition': {
                'total_customers': total_customers_ever,
                'period_customers': unique_customers,
            },
            'alerts': alerts,
            'suggestions': suggestions,
        })

    @staticmethod
    def _empty_response():
        return {
            'period_days': 30,
            'demand_visibility': {'total_views': 0, 'total_clicks': 0, 'map_visibility': 0},
            'conversion_funnel': {'views': 0, 'clicks': 0, 'bookings': 0, 'redemptions': 0,
                                  'click_rate': 0, 'booking_rate': 0, 'redemption_rate': 0},
            'revenue': {'total_revenue': 0, 'revenue_per_deal': 0, 'avg_spend_per_customer': 0,
                        'daily_breakdown': [], 'weekly_breakdown': []},
            'time_heatmap': {'hourly': [0]*24, 'daily': [0]*7},
            'deal_performance': [],
            'customer_behaviour': {'new_customers': 0, 'repeat_customers': 0,
                                    'avg_visit_frequency': 0, 'avg_group_size': 0},
            'traffic_source': {'near_you': 0, 'search': 0, 'top_rated': 0, 'notifications': 0},
            'rating_breakdown': {'overall': 0, 'food': 0, 'service': 0, 'ambience': 0},
            'competitor_insights': [],
            'customer_acquisition': {'total_customers': 0, 'period_customers': 0},
            'alerts': [{'type': 'no_restaurants', 'severity': 'info',
                        'message': 'Add a restaurant to start seeing analytics.'}],
            'suggestions': [{'type': 'add_restaurant', 'action': 'add_restaurant',
                             'message': 'Register your restaurant to unlock insights.'}],
        }


from rest_framework import mixins

class RestaurantPartnerRequestViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    ViewSet for public 'Join as Restaurant Partner' inquiries.
    POST: Submit a new inquiry form.
    """
    queryset = RestaurantPartnerRequest.objects.all()
    serializer_class = RestaurantPartnerRequestSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        instance = serializer.save()

        # Send email notification after successful creation
        subject = f"🔔 New Restaurant Partner Inquiry: {instance.restaurant_name}"

        # Proper layout for the email
        email_body = (
            f"Dear Admin,\n\n"
            f"You have received a new 'Join as Restaurant Partner' inquiry through Discount Buddy.\n\n"
            f"DETAILS:\n"
            f"----------------------------------------\n"
            f"Restaurant Name:    {instance.restaurant_name}\n"
            f"Owner/Contact Name: {instance.contact_name}\n"
            f"Email Address:      {instance.email}\n"
            f"Phone Number:       {instance.phone}\n"
            f"City Location:      {instance.city_name}\n"
            f"Website:            {instance.website or 'Not provided'}\n"
            f"----------------------------------------\n\n"
            f"ADDITIONAL COMMENTS:\n"
            f"{instance.comments or 'No comments provided.'}\n\n"
            f"Date Submitted: {instance.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"Regards,\n"
            f"Discount Buddy System"
        )

        try:
            send_mail(
                subject=subject,
                message=email_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=["info@markitupgroup.com"],
                fail_silently=False,
            )
        except Exception as e:
            # We log it but don't break the user's successful submission
            print(f"Error sending partner request email: {e}")


class UserLoyaltyCardViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Customer loyalty cards across all restaurants.
    List all loyalty progress or retrieve for a specific restaurant.
    """
    serializer_class = UserLoyaltyCardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = UserRestaurantLoyalty.objects.filter(
            user=self.request.user,
            restaurant__loyalty_card_enabled=True,
            restaurant__is_active=True,
        ).select_related("restaurant", "user").prefetch_related("restaurant__images")

        if self.action == "list":
            queryset = queryset.filter(
                Q(current_cycle_redemptions__gt=0) | Q(is_reward_eligible=True)
            ).order_by("-is_reward_eligible", "-current_cycle_redemptions", "-updated_at")

        return queryset

    def get_object(self):
        restaurant_id = self.kwargs.get("pk")
        try:
            return self.get_queryset().get(restaurant_id=restaurant_id)
        except UserRestaurantLoyalty.DoesNotExist:
            restaurant = Restaurant.objects.filter(
                pk=restaurant_id,
                loyalty_card_enabled=True,
                is_active=True,
            ).first()
            if not restaurant:
                raise NotFound("Restaurant not found or loyalty card is not enabled.")
            loyalty, _ = UserRestaurantLoyalty.objects.get_or_create(
                user=self.request.user,
                restaurant=restaurant,
            )
            return loyalty


class MerchantLoyaltyCustomersView(APIView):
    """List customers with loyalty progress for a merchant's restaurant."""

    permission_classes = [IsRestaurant]

    def get(self, request):
        restaurant_id = request.query_params.get("restaurant_id")
        if not restaurant_id:
            return Response(
                {"error": "restaurant_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        restaurant_qs = get_merchant_restaurants_queryset(request.user)
        try:
            restaurant = restaurant_qs.get(pk=restaurant_id)
        except Restaurant.DoesNotExist:
            return Response({"error": "Restaurant not found."}, status=status.HTTP_404_NOT_FOUND)

        eligible_only = request.query_params.get("eligible_only", "").lower() in ("true", "1", "yes")
        queryset = UserRestaurantLoyalty.objects.filter(
            restaurant=restaurant,
        ).select_related("user", "restaurant")

        if eligible_only:
            queryset = queryset.filter(is_reward_eligible=True)

        serializer = MerchantLoyaltyCustomerSerializer(
            queryset.order_by("-is_reward_eligible", "-updated_at"),
            many=True,
            context={"request": request},
        )
        return Response({
            "restaurant_id": restaurant.id,
            "restaurant_name": restaurant.name,
            "loyalty_card_enabled": restaurant.loyalty_card_enabled,
            "required_redemptions": restaurant.loyalty_required_redemptions,
            "reward_description": restaurant.loyalty_reward_description,
            "customers": serializer.data,
            "count": len(serializer.data),
        })


class MerchantLoyaltyClaimRewardView(APIView):
    """Mark a customer's loyalty reward as claimed."""

    permission_classes = [IsRestaurant]

    def post(self, request):
        qr_data = request.data.get("qr_data")
        reward_code = request.data.get("reward_code")
        
        restaurant = None
        customer = None
        
        if not qr_data and not reward_code:
            serializer = LoyaltyRewardClaimSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
    
            restaurant_id = serializer.validated_data["restaurant_id"]
            user_id = serializer.validated_data["user_id"]
    
            restaurant_qs = get_merchant_restaurants_queryset(request.user)
            try:
                restaurant = restaurant_qs.get(pk=restaurant_id)
            except Restaurant.DoesNotExist:
                return Response({"error": "Restaurant not found."}, status=status.HTTP_404_NOT_FOUND)
    
            from users.models import User
            try:
                customer = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                return Response({"error": "Customer not found."}, status=status.HTTP_404_NOT_FOUND)

        success, message, loyalty = claim_loyalty_reward(
            actor=request.user,
            qr_data=qr_data,
            reward_code=reward_code,
            restaurant=restaurant,
            customer_user=customer,
        )

        if not success:
            return Response({"success": False, "reason": message}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "success": True,
            "reason": message,
            "loyalty": MerchantLoyaltyCustomerSerializer(loyalty, context={"request": request}).data,
        })


class MerchantLoyaltyHistoryView(APIView):
    """Audit log of loyalty redemption events for a restaurant."""

    permission_classes = [IsRestaurant]

    def get(self, request):
        restaurant_id = request.query_params.get("restaurant_id")
        if not restaurant_id:
            return Response(
                {"error": "restaurant_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        restaurant_qs = get_merchant_restaurants_queryset(request.user)
        try:
            restaurant = restaurant_qs.get(pk=restaurant_id)
        except Restaurant.DoesNotExist:
            return Response({"error": "Restaurant not found."}, status=status.HTTP_404_NOT_FOUND)

        queryset = LoyaltyRedemptionRecord.objects.filter(
            restaurant=restaurant,
        ).select_related("user", "deal_use", "deal_use__deal")

        user_id = request.query_params.get("user_id")
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        serializer = LoyaltyRedemptionRecordSerializer(
            queryset.order_by("-created_at")[:200],
            many=True,
        )
        return Response({
            "restaurant_id": restaurant.id,
            "records": serializer.data,
            "count": len(serializer.data),
        })

