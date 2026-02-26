import math
from django.db.models import Q, Count, F
from django.utils import timezone
from django.core.cache import cache
from rest_framework import generics, viewsets, status, filters
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

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
)
from .serializers import (
    CountrySerializer,
    CitySerializer,
    RestaurantCategorySerializer,
    RestaurantSerializer,
    RestaurantListSerializer,
    DealSerializer,
    DealListSerializer,
    SavedRestaurantSerializer,
    SavedDealSerializer,
    DealUseSerializer,
    DealUseCreateSerializer,
    DealRedemptionRequestSerializer,
    CuisineSerializer,
    ReviewSerializer,
    ReviewCreateSerializer,
    BookingSerializer,
    BookingCreateSerializer,
    BookingManagementSerializer,
    MenuCategorySerializer,
    MenuItemSerializer,
    MenuItemCreateSerializer,
    OpeningSlotSerializer,
    RestaurantDetailSerializer,
    RestaurantProfileSerializer,
    MysteryVisitSerializer,
    MysteryVisitSubmitSerializer,
    MysteryEvidenceSerializer,
)
from .services import redeem_deal, calculate_distance, km_to_miles
from users.permissions import (
    IsMerchant,
    IsUser,
    IsRestaurant,
    IsRestaurantOwner,
    IsMysteryGuest,
)




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


class RestaurantViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for restaurants"""
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = RestaurantFilter
    search_fields = ["name", "description", "address", "city__name"]
    ordering_fields = ["name", "created_at", "is_featured"]
    ordering = ["-is_featured", "-created_at"]
    
    def get_serializer_class(self):
        if self.action == "list":
            return RestaurantListSerializer
        return RestaurantSerializer
    
    def get_queryset(self):
        queryset = Restaurant.objects.filter(
            is_active=True,
            verified=True
        ).select_related("city", "city__country").prefetch_related(
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
        
        # Filter by category slug if provided
        category_slug = self.request.query_params.get("category")
        if category_slug:
            queryset = queryset.filter(categories__slug=category_slug)
        
        # Nearby restaurants (requires lat/long)
        lat = self.request.query_params.get("latitude")
        lon = self.request.query_params.get("longitude")
        radius = self.request.query_params.get("radius", 10)  # default 10km
        
        if lat and lon:
            try:
                lat = float(lat)
                lon = float(lon)
                radius = float(radius)
                
                # Filter restaurants within approximate radius
                # Simple bounding box filter (not perfect but fast)
                lat_delta = radius / 111.0  # roughly 1 degree = 111km
                lon_delta = radius / (111.0 * abs(math.cos(math.radians(lat))))
                
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
        - radius (optional, miles; default 10)
        """
        lat = request.query_params.get("latitude")
        lon = request.query_params.get("longitude")
        radius_miles = float(request.query_params.get("radius", 10))
        
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
        
        # Convert radius from miles to km for calculations
        radius_km = radius_miles * 1.60934

        # Get all restaurants within bounding box (km)
        lat_delta = radius_km / 111.0
        lon_delta = radius_km / (111.0 * abs(math.cos(math.radians(lat))))
        
        restaurants = Restaurant.objects.filter(
            is_active=True,
            verified=True,
            latitude__gte=lat - lat_delta,
            latitude__lte=lat + lat_delta,
            longitude__gte=lon - lon_delta,
            longitude__lte=lon + lon_delta,
            latitude__isnull=False,
            longitude__isnull=False
        ).select_related("city", "city__country").prefetch_related("images")
        
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
                        restaurants_with_distance.append((restaurant, distance_miles))
        
        # Sort by distance
        restaurants_with_distance.sort(key=lambda x: x[1])
        restaurants = []
        for r, distance_miles in restaurants_with_distance:
            r._distance_miles = distance_miles
            restaurants.append(r)
        
        serializer = RestaurantListSerializer(restaurants, many=True, context={"request": request})
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
            "deal", "deal__restaurant"
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
        """Get or create Merchant instance for the current user"""
        from vouchers.models import Merchant
        from users.models import UserProfile
        
        # Check if user has merchant role
        try:
            if self.request.user.profile.role != UserProfile.ROLE_MERCHANT:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("User is not a merchant.")
        except UserProfile.DoesNotExist:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("User profile not found.")
        
        # Get or create Merchant instance
        merchant, created = Merchant.objects.get_or_create(
            user=self.request.user,
            defaults={'name': self.request.user.username or self.request.user.email}
        )
        return merchant
    
    def get_queryset(self):
        # Get merchant's restaurants
        merchant = self.get_merchant()
        return Restaurant.objects.filter(
            merchant=merchant
        ).select_related("city", "city__country").prefetch_related(
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
        """Get or create Merchant instance for the current user"""
        from vouchers.models import Merchant
        from users.models import UserProfile
        
        # Check if user has merchant role
        try:
            if self.request.user.profile.role != UserProfile.ROLE_MERCHANT:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("User is not a merchant.")
        except UserProfile.DoesNotExist:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("User profile not found.")
        
        # Get or create Merchant instance
        merchant, created = Merchant.objects.get_or_create(
            user=self.request.user,
            defaults={'name': self.request.user.username or self.request.user.email}
        )
        return merchant
    
    def get_queryset(self):
        # Get deals for merchant's restaurants
        merchant = self.get_merchant()
        return Deal.objects.filter(
            restaurant__merchant=merchant
        ).select_related("restaurant").prefetch_related("images")
    
    def perform_create(self, serializer):
        restaurant_id = self.request.data.get("restaurant")
        merchant = self.get_merchant()
        
        # Verify restaurant belongs to merchant
        try:
            restaurant = Restaurant.objects.get(id=restaurant_id, merchant=merchant)
        except Restaurant.DoesNotExist:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Restaurant not found or does not belong to you")
        
        serializer.save(restaurant=restaurant)


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
        from django.db.models import Avg, Count
        
        # Get query parameters
        params = request.query_params
        search_query = params.get("q", "").strip()
        cuisine_id = params.get("cuisine")
        city_id = params.get("city")
        latitude = params.get("latitude") or params.get("lat")
        longitude = params.get("longitude") or params.get("lon")
        now_open = params.get("now_open", "false").lower() == "true"
        radius_miles = float(params.get("radius", 10))  # default 10 miles
        radius_km = radius_miles * 1.60934
        
        # Base queryset
        queryset = Restaurant.objects.filter(
            is_active=True,
            verified=True
        ).select_related("city", "city__country").prefetch_related(
            "categories", "cuisines", "images"
        ).annotate(
            average_rating=Avg("reviews__rating"),
            reviews_count=Count("reviews"),
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
        
        # Nearby filter (requires lat/lng)
        nearby_restaurants = None
        if latitude and longitude:
            try:
                lat = float(latitude)
                lon = float(longitude)
                
                # Bounding box filter
                lat_delta = radius_km / 111.0
                lon_delta = radius_km / (111.0 * abs(math.cos(math.radians(lat))))
                
                nearby_qs = queryset.filter(
                    latitude__gte=lat - lat_delta,
                    latitude__lte=lat + lat_delta,
                    longitude__gte=lon - lon_delta,
                    longitude__lte=lon + lon_delta,
                    latitude__isnull=False,
                    longitude__isnull=False
                )
                
                # Calculate distances and sort
                restaurants_with_distance = []
                for restaurant in nearby_qs:
                    if restaurant.latitude and restaurant.longitude:
                        dist_km = calculate_distance(
                            lat, lon,
                            float(restaurant.latitude),
                            float(restaurant.longitude)
                        )
                        if dist_km and dist_km <= radius_km:
                            dist_miles = km_to_miles(dist_km)
                            restaurant._distance_miles = dist_miles
                            restaurants_with_distance.append((restaurant, dist_miles))
                
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
        
        # Cuisine-based segregation
        cuisines = Cuisine.objects.filter(
            is_active=True,
            restaurants__in=queryset
        ).distinct().annotate(
            restaurants_count=Count("restaurants", filter=Q(restaurants__in=queryset))
        )
        
        cuisine_data = []
        for cuisine in cuisines:
            cuisine_restaurants = list(queryset.filter(cuisines=cuisine)[:10])
            cuisine_restaurants = populate_distances(cuisine_restaurants)
            cuisine_data.append({
                "cuisine": CuisineSerializer(cuisine, context={"request": request}).data,
                "restaurants": RestaurantListSerializer(
                    cuisine_restaurants,
                    many=True,
                    context={"request": request}
                ).data
            })
        
        # All restaurants (card format) – keep default ordering but include leaderboard_score in payload
        all_restaurants = list(queryset.order_by("-is_featured", "-average_rating")[:50])
        all_restaurants = populate_distances(all_restaurants)
        
        return Response({
            "search_query": search_query,
            "now_open": RestaurantListSerializer(
                now_open_restaurants or [],
                many=True,
                context={"request": request}
            ).data,
            "nearby": RestaurantListSerializer(
                nearby_restaurants or [],
                many=True,
                context={"request": request}
            ).data,
            "cuisines": cuisine_data,
            "top_10": RestaurantListSerializer(
                top_10,
                many=True,
                context={"request": request}
            ).data,
            "all_restaurants": RestaurantListSerializer(
                all_restaurants,
                many=True,
                context={"request": request}
            ).data
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
            "menu_categories__items", "opening_slots", "deals"
        )
    
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
        
        return Response(
            {"detail": "Booking cancelled successfully"},
            status=status.HTTP_200_OK
        )


class ProfileStatsView(generics.GenericAPIView):
    """
    User profile stats: deals claimed, money saved, user level, restaurants visited, cities visited
    """
    permission_classes = [IsUser]
    
    def get(self, request):
        user = request.user
        
        # Deals claimed (DealUse)
        deals_claimed = DealUse.objects.filter(user=user).count()
        
        # Money saved (sum of discount amounts from used deals)
        from django.db.models import Sum
        money_saved = DealUse.objects.filter(
            user=user
        ).aggregate(
            total_saved=Sum("deal__discount_amount")
        )["total_saved"] or 0
        
        # Restaurants visited (unique restaurants from bookings and deal uses)
        from django.db.models import Count
        restaurants_visited = Booking.objects.filter(
            user=user,
            status__in=[Booking.STATUS_CONFIRMED, Booking.STATUS_COMPLETED]
        ).values("restaurant").distinct().count()
        
        restaurants_from_deals = DealUse.objects.filter(
            user=user
        ).values("deal__restaurant").distinct().count()
        
        total_restaurants_visited = max(restaurants_visited, restaurants_from_deals)
        
        # Cities visited
        cities_visited = Booking.objects.filter(
            user=user,
            status__in=[Booking.STATUS_CONFIRMED, Booking.STATUS_COMPLETED]
        ).values("restaurant__city").distinct().count()
        
        # User level (logic-based: Bronze, Silver, Gold, Platinum)
        total_activity = deals_claimed + total_restaurants_visited
        if total_activity >= 100:
            user_level = "Platinum"
        elif total_activity >= 50:
            user_level = "Gold"
        elif total_activity >= 20:
            user_level = "Silver"
        else:
            user_level = "Bronze"
        
        # Favourite restaurants count
        favourite_count = SavedRestaurant.objects.filter(user=user).count()
        
        # Reviews count
        reviews_count = Review.objects.filter(user=user).count()
        
        return Response({
            "deals_claimed": deals_claimed,
            "money_saved": float(money_saved),
            "user_level": user_level,
            "restaurants_visited": total_restaurants_visited,
            "cities_visited": cities_visited,
            "favourite_restaurants": favourite_count,
            "reviews_written": reviews_count
        })


# ==================== RESTAURANT MANAGEMENT VIEWS ====================

class RestaurantManagementViewSet(viewsets.ModelViewSet):
    """ViewSet for restaurant owners to manage their restaurant"""
    serializer_class = RestaurantSerializer
    permission_classes = [IsRestaurant]
    
    def get_queryset(self):
        # Get restaurants owned by the user
        user = self.request.user
        try:
            if hasattr(user, 'restaurant_profile'):
                return Restaurant.objects.filter(
                    owner_profile__user=user
                )
            # Fallback to merchant
            if hasattr(user, 'merchant'):
                return Restaurant.objects.filter(merchant=user.merchant)
        except:
            pass
        return Restaurant.objects.none()
    
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


class MenuManagementViewSet(viewsets.ModelViewSet):
    """ViewSet for restaurant owners to manage menu categories and items"""
    serializer_class = MenuCategorySerializer
    permission_classes = [IsRestaurant]
    
    def get_queryset(self):
        # Get menu categories for user's restaurants
        user = self.request.user
        restaurant_ids = []
        try:
            if hasattr(user, 'restaurant_profile'):
                restaurant_ids = [user.restaurant_profile.restaurant_id]
            elif hasattr(user, 'merchant'):
                restaurant_ids = list(
                    Restaurant.objects.filter(merchant=user.merchant).values_list("id", flat=True)
                )
        except:
            pass
        
        return MenuCategory.objects.filter(restaurant_id__in=restaurant_ids)
    
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
        # Get opening slots for user's restaurants
        user = self.request.user
        restaurant_ids = []
        try:
            if hasattr(user, 'restaurant_profile'):
                restaurant_ids = [user.restaurant_profile.restaurant_id]
            elif hasattr(user, 'merchant'):
                restaurant_ids = list(
                    Restaurant.objects.filter(merchant=user.merchant).values_list("id", flat=True)
                )
        except:
            pass
        
        return OpeningSlot.objects.filter(restaurant_id__in=restaurant_ids)
    
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
        # Get reviews for user's restaurants
        user = self.request.user
        restaurant_ids = []
        try:
            if hasattr(user, 'restaurant_profile'):
                restaurant_ids = [user.restaurant_profile.restaurant_id]
            elif hasattr(user, 'merchant'):
                restaurant_ids = list(
                    Restaurant.objects.filter(merchant=user.merchant).values_list("id", flat=True)
                )
        except:
            pass
        
        return Review.objects.filter(restaurant_id__in=restaurant_ids).select_related("user")


class RestaurantBookingsManagementViewSet(viewsets.ModelViewSet):
    """ViewSet for restaurant owners to view and update their restaurant bookings"""
    permission_classes = [IsRestaurant]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    
    def get_serializer_class(self):
        if self.action in ["update", "partial_update"]:
            return BookingManagementSerializer
        return BookingSerializer
    filterset_fields = ["status"]
    ordering_fields = ["booking_date"]
    ordering = ["-booking_date"]
    http_method_names = ["get", "patch", "head", "options"]
    
    def get_queryset(self):
        # Get bookings for user's restaurants
        user = self.request.user
        restaurant_ids = []
        try:
            if hasattr(user, 'restaurant_profile'):
                restaurant_ids = [user.restaurant_profile.restaurant_id]
            elif hasattr(user, 'merchant'):
                restaurant_ids = list(
                    Restaurant.objects.filter(merchant=user.merchant).values_list("id", flat=True)
                )
        except:
            pass
        
        return Booking.objects.filter(
            restaurant_id__in=restaurant_ids
        ).select_related("user", "restaurant")


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
        user = self.request.user
        restaurant_ids = []
        try:
            if hasattr(user, 'restaurant_profile'):
                restaurant_ids = [user.restaurant_profile.restaurant_id]
            elif hasattr(user, 'merchant'):
                restaurant_ids = list(
                    Restaurant.objects.filter(merchant=user.merchant).values_list("id", flat=True)
                )
        except:
            pass
        
        return MenuItem.objects.filter(category__restaurant_id__in=restaurant_ids)
    
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

