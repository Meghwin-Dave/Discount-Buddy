import math
from django.db.models import Q, Count
from django.db import transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import (
    NeoTasteUser, City, Category, Restaurant, Offer, Redemption, OTP
)
from .serializers import (
    CitySerializer, CategorySerializer,
    RestaurantListSerializer, RestaurantDetailSerializer,
    OfferDetailSerializer, OfferListSerializer,
    RedemptionSerializer, RedemptionCreateSerializer,
    UserProfileSerializer, CitySelectionSerializer,
    LoginSerializer, VerifyOTPSerializer, HomeScreenSerializer, LogoutSerializer
)
from .utils import calculate_distance, generate_otp


class LoginView(APIView):
    """Send OTP to mobile number"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        mobile_number = serializer.validated_data['mobile_number']
        
        # Check rate limiting (simple implementation)
        recent_otps = OTP.objects.filter(
            mobile_number=mobile_number,
            created_at__gte=timezone.now() - timezone.timedelta(minutes=1)
        ).count()
        
        if recent_otps >= 3:
            return Response(
                {"error": "Too many OTP requests. Please try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        # Generate OTP
        otp_code = generate_otp()
        expires_at = timezone.now() + timezone.timedelta(minutes=5)
        
        # Create OTP record
        OTP.objects.create(
            mobile_number=mobile_number,
            otp_code=otp_code,
            expires_at=expires_at
        )
        
        # In production, send SMS here
        # For development, you might want to log or return OTP
        # In production, remove this and send via SMS service
        print(f"OTP for {mobile_number}: {otp_code}")  # Remove in production
        
        return Response({
            "message": "OTP sent successfully",
            "mobile_number": mobile_number,
            "otp_expires_in": 300
        }, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    """Verify OTP and authenticate user"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        mobile_number = serializer.validated_data['mobile_number']
        
        # Get or create user
        user, created = NeoTasteUser.objects.get_or_create(
            mobile_number=mobile_number,
            defaults={'is_active': True}
        )
        
        if not user.is_active:
            return Response(
                {"error": "User account is inactive"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserProfileSerializer(user).data
        }, status=status.HTTP_200_OK)


class CityListView(generics.ListAPIView):
    """List all active cities"""
    queryset = City.objects.filter(is_active=True)
    serializer_class = CitySerializer
    permission_classes = [AllowAny]


class SelectCityView(APIView):
    """Select city for authenticated user"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = CitySelectionSerializer(data=request.data, instance=request.user)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save()
        
        return Response({
            "message": "City selected successfully",
            "user": UserProfileSerializer(request.user).data
        }, status=status.HTTP_200_OK)


class HomeView(APIView):
    """Get home screen data"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        if not user.selected_city:
            return Response(
                {"error": "Please select a city first"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get featured restaurants in selected city
        featured_restaurants = Restaurant.objects.filter(
            city=user.selected_city,
            is_active=True,
            is_featured=True
        ).select_related('city').prefetch_related('categories')[:10]
        
        # Get all active categories
        categories = Category.objects.filter(is_active=True)[:10]
        
        # Get active offers count in selected city
        now = timezone.now()
        active_offers_count = Offer.objects.filter(
            restaurant__city=user.selected_city,
            restaurant__is_active=True,
            is_active=True,
            expiry_date__gt=now
        ).count()
        
        data = {
            "featured_restaurants": RestaurantListSerializer(
                featured_restaurants,
                many=True,
                context={'request': request}
            ).data,
            "categories": CategorySerializer(categories, many=True).data,
            "active_offers_count": active_offers_count
        }
        
        serializer = HomeScreenSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RestaurantViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for restaurants"""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return RestaurantDetailSerializer
        return RestaurantListSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        if not user.selected_city:
            return Restaurant.objects.none()
        
        queryset = Restaurant.objects.filter(
            city=user.selected_city,
            is_active=True
        ).select_related('city').prefetch_related('categories', 'offers')
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(categories__id=category)
        
        # Filter by offers availability
        has_offers = self.request.query_params.get('has_offers')
        if has_offers and has_offers.lower() == 'true':
            now = timezone.now()
            queryset = queryset.filter(
                offers__is_active=True,
                offers__expiry_date__gt=now
            ).distinct()
        
        # Distance filter
        latitude = self.request.query_params.get('latitude')
        longitude = self.request.query_params.get('longitude')
        max_distance = self.request.query_params.get('distance')
        
        if latitude and longitude and max_distance:
            try:
                lat = float(latitude)
                lon = float(longitude)
                max_dist = float(max_distance)
                
                # Store user coordinates in request for serializer
                self.request.user_lat = lat
                self.request.user_lon = lon
                
                # Filter by approximate bounding box
                lat_delta = max_dist / 111.0
                lon_delta = max_dist / (111.0 * abs(math.cos(math.radians(lat))))
                
                queryset = queryset.filter(
                    latitude__gte=lat - lat_delta,
                    latitude__lte=lat + lat_delta,
                    longitude__gte=lon - lon_delta,
                    longitude__lte=lon + lon_delta,
                    latitude__isnull=False,
                    longitude__isnull=False
                )
                
                # Calculate actual distances and filter
                restaurants_with_distance = []
                for restaurant in queryset:
                    if restaurant.latitude and restaurant.longitude:
                        distance = calculate_distance(
                            lat, lon,
                            float(restaurant.latitude),
                            float(restaurant.longitude)
                        )
                        if distance and distance <= max_dist:
                            restaurants_with_distance.append((restaurant, distance))
                
                # Sort by distance
                restaurants_with_distance.sort(key=lambda x: x[1])
                queryset = Restaurant.objects.filter(
                    id__in=[r[0].id for r in restaurants_with_distance]
                ).select_related('city').prefetch_related('categories', 'offers')
                
            except (ValueError, TypeError):
                pass
        
        return queryset


class OfferViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for offers"""
    permission_classes = [IsAuthenticated]
    serializer_class = OfferDetailSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        if not user.selected_city:
            return Offer.objects.none()
        
        now = timezone.now()
        return Offer.objects.filter(
            restaurant__city=user.selected_city,
            restaurant__is_active=True,
            is_active=True,
            expiry_date__gt=now
        ).select_related('restaurant', 'restaurant__city')
    
    @action(detail=True, methods=['post'])
    def redeem(self, request, pk=None):
        """Redeem an offer"""
        offer = self.get_object()
        
        # Validate redemption
        if not offer.is_valid():
            return Response(
                {"error": "Offer is not active or has expired"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not offer.can_user_redeem(request.user):
            return Response(
                {"error": "You have reached the maximum redemptions for this offer"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create redemption with transaction
        serializer = RedemptionCreateSerializer(
            data={},
            context={'request': request, 'offer': offer}
        )
        
        if serializer.is_valid():
            redemption = serializer.save()
            return Response({
                "id": redemption.id,
                "offer": {
                    "id": offer.id,
                    "title": offer.title,
                    "restaurant": {
                        "id": offer.restaurant.id,
                        "name": offer.restaurant.name
                    }
                },
                "status": redemption.status,
                "redeemed_at": redemption.redeemed_at,
                "message": "Offer redeemed successfully"
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WalletView(generics.ListAPIView):
    """Get user's redemption history"""
    permission_classes = [IsAuthenticated]
    serializer_class = RedemptionSerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = Redemption.objects.filter(
            user=user
        ).select_related('offer', 'offer__restaurant').order_by('-redeemed_at')
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset


class ProfileView(APIView):
    """Get user profile"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """Logout user"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        refresh_token = serializer.validated_data['refresh']
        
        try:
            token = RefreshToken(refresh_token)
            # Try to blacklist if blacklist app is installed
            try:
                token.blacklist()
            except AttributeError:
                # Blacklist not configured, just validate token
                pass
            return Response(
                {"message": "Logged out successfully"},
                status=status.HTTP_200_OK
            )
        except TokenError:
            return Response(
                {"error": "Invalid refresh token"},
                status=status.HTTP_400_BAD_REQUEST
            )
