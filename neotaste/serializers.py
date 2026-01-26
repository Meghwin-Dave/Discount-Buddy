from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
from django.core.validators import RegexValidator

from .models import (
    NeoTasteUser, City, Category, Restaurant, Offer, Redemption, OTP
)


class CitySerializer(serializers.ModelSerializer):
    """Serializer for City model"""
    
    class Meta:
        model = City
        fields = ['id', 'name', 'is_active']


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model"""
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'is_active']


class RestaurantListSerializer(serializers.ModelSerializer):
    """Serializer for restaurant list view"""
    
    city = CitySerializer(read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    active_offers_count = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()
    
    class Meta:
        model = Restaurant
        fields = [
            'id', 'name', 'address', 'city', 'categories',
            'active_offers_count', 'distance', 'is_featured'
        ]
    
    def get_active_offers_count(self, obj):
        return obj.get_active_offers_count()
    
    def get_distance(self, obj):
        """Calculate distance if user coordinates provided"""
        request = self.context.get('request')
        if request and hasattr(request, 'user_lat') and hasattr(request, 'user_lon'):
            if obj.latitude and obj.longitude:
                from .utils import calculate_distance
                return round(calculate_distance(
                    request.user_lat, request.user_lon,
                    float(obj.latitude), float(obj.longitude)
                ), 2)
        return None


class RestaurantDetailSerializer(serializers.ModelSerializer):
    """Serializer for restaurant detail view"""
    
    city = CitySerializer(read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    offers = serializers.SerializerMethodField()
    
    class Meta:
        model = Restaurant
        fields = [
            'id', 'name', 'description', 'address', 'city',
            'categories', 'offers', 'is_featured'
        ]
    
    def get_offers(self, obj):
        """Get active offers for this restaurant"""
        now = timezone.now()
        active_offers = obj.offers.filter(
            is_active=True,
            expiry_date__gt=now
        )
        return OfferListSerializer(active_offers, many=True, context=self.context).data


class OfferListSerializer(serializers.ModelSerializer):
    """Serializer for offer list view"""
    
    class Meta:
        model = Offer
        fields = [
            'id', 'title', 'description', 'expiry_date',
            'max_redemptions_per_user', 'terms_and_conditions'
        ]


class OfferDetailSerializer(serializers.ModelSerializer):
    """Serializer for offer detail view"""
    
    restaurant = serializers.SerializerMethodField()
    user_redemptions_count = serializers.SerializerMethodField()
    can_redeem = serializers.SerializerMethodField()
    
    class Meta:
        model = Offer
        fields = [
            'id', 'restaurant', 'title', 'description', 'expiry_date',
            'max_redemptions_per_user', 'terms_and_conditions',
            'user_redemptions_count', 'can_redeem'
        ]
    
    def get_restaurant(self, obj):
        return {
            'id': obj.restaurant.id,
            'name': obj.restaurant.name,
            'address': obj.restaurant.address
        }
    
    def get_user_redemptions_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.redemptions.filter(user=request.user).count()
        return 0
    
    def get_can_redeem(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.can_user_redeem(request.user)
        return False


class RedemptionSerializer(serializers.ModelSerializer):
    """Serializer for redemption model"""
    
    offer = serializers.SerializerMethodField()
    
    class Meta:
        model = Redemption
        fields = ['id', 'offer', 'status', 'redeemed_at']
    
    def get_offer(self, obj):
        return {
            'id': obj.offer.id,
            'title': obj.offer.title,
            'restaurant': {
                'id': obj.offer.restaurant.id,
                'name': obj.offer.restaurant.name
            },
            'expiry_date': obj.offer.expiry_date
        }


class RedemptionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating redemption"""
    
    class Meta:
        model = Redemption
        fields = []
    
    def validate(self, attrs):
        request = self.context.get('request')
        offer = self.context.get('offer')
        
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required")
        
        if not offer.is_valid():
            raise serializers.ValidationError("Offer is not active or has expired")
        
        if not offer.can_user_redeem(request.user):
            raise serializers.ValidationError(
                "You have reached the maximum redemptions for this offer"
            )
        
        return attrs
    
    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get('request')
        offer = self.context.get('offer')
        
        redemption, created = Redemption.objects.get_or_create(
            user=request.user,
            offer=offer,
            defaults={'status': Redemption.STATUS_REDEEMED}
        )
        
        if not created:
            raise serializers.ValidationError("You have already redeemed this offer")
        
        return redemption


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    
    selected_city = CitySerializer(read_only=True)
    
    class Meta:
        model = NeoTasteUser
        fields = [
            'id', 'mobile_number', 'selected_city',
            'membership_status', 'created_at'
        ]
        read_only_fields = ['id', 'mobile_number', 'created_at']


class CitySelectionSerializer(serializers.Serializer):
    """Serializer for city selection"""
    
    city_id = serializers.IntegerField()
    
    def validate_city_id(self, value):
        try:
            city = City.objects.get(id=value, is_active=True)
        except City.DoesNotExist:
            raise serializers.ValidationError("City not found or inactive")
        return value
    
    def update(self, instance, validated_data):
        city_id = validated_data['city_id']
        city = City.objects.get(id=city_id)
        instance.selected_city = city
        instance.save(update_fields=['selected_city'])
        return instance


class LoginSerializer(serializers.Serializer):
    """Serializer for login (OTP request)"""
    
    mobile_number = serializers.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            )
        ]
    )
    
    def validate_mobile_number(self, value):
        # Normalize mobile number
        if not value.startswith('+'):
            # Assume default country code if not provided
            # In production, you might want to handle this differently
            value = '+' + value
        return value


class VerifyOTPSerializer(serializers.Serializer):
    """Serializer for OTP verification"""
    
    mobile_number = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6, min_length=6)
    
    def validate(self, attrs):
        mobile_number = attrs['mobile_number']
        otp_code = attrs['otp']
        
        # Normalize mobile number
        if not mobile_number.startswith('+'):
            mobile_number = '+' + mobile_number
        
        # Find valid OTP
        try:
            otp_obj = OTP.objects.filter(
                mobile_number=mobile_number,
                otp_code=otp_code,
                is_verified=False
            ).latest('created_at')
            
            if not otp_obj.is_valid():
                raise serializers.ValidationError("Invalid or expired OTP")
            
            # Mark OTP as verified
            otp_obj.is_verified = True
            otp_obj.save(update_fields=['is_verified'])
            
            attrs['otp_obj'] = otp_obj
            attrs['mobile_number'] = mobile_number
            
        except OTP.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired OTP")
        
        return attrs


class HomeScreenSerializer(serializers.Serializer):
    """Serializer for home screen data"""
    
    featured_restaurants = RestaurantListSerializer(many=True)
    categories = CategorySerializer(many=True)
    active_offers_count = serializers.IntegerField()


class LogoutSerializer(serializers.Serializer):
    """Serializer for logout"""
    
    refresh = serializers.CharField()
