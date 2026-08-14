from rest_framework import serializers
from django.utils import timezone

from core.serializers_image import ProcessedImageOutputMixin
from core.services.image_service import ImageProcessingService
from .opening_hours_sync import sync_opening_slots_from_opening_hours
from .models import (
    Country,
    City,
    RestaurantCategory,
    Restaurant,
    Deal,
    RestaurantImage,
    DealImage,
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
    RestaurantPartnerRequest,
    UserRestaurantLoyalty,
    LoyaltyRedemptionRecord,
)


def _get_primary_restaurant_image_url(restaurant, request=None):
    primary_img = restaurant.images.filter(is_primary=True).first() or restaurant.images.first()
    if not primary_img:
        return None
    urls = ImageProcessingService.get_image_urls(primary_img, request=request)
    return urls.get("large") or urls.get("medium")


def _get_primary_deal_image_url(deal, request=None):
    primary_img = deal.images.filter(is_primary=True).first() or deal.images.first()
    if not primary_img:
        return None
    urls = ImageProcessingService.get_image_urls(primary_img, request=request)
    return urls.get("large") or urls.get("medium")
from .services import build_loyalty_progress_payload


class CountrySerializer(serializers.ModelSerializer):
    cities_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Country
        fields = ("id", "name", "code", "flag_emoji", "cities_count", "created_at")
        
    def get_cities_count(self, obj):
        return obj.cities.filter(is_active=True).count()


class CitySerializer(serializers.ModelSerializer):
    country = CountrySerializer(read_only=True)
    restaurants_count = serializers.SerializerMethodField()
    active_deals_count = serializers.SerializerMethodField()
    
    class Meta:
        model = City
        fields = (
            "id", "name", "slug", "country", "latitude", "longitude",
            "is_active", "restaurants_count", "active_deals_count", "created_at"
        )
        
    def get_restaurants_count(self, obj):
        return obj.restaurants.filter(is_active=True, verified=True).count()
    
    def get_active_deals_count(self, obj):
        from django.utils import timezone
        now = timezone.now()
        return Deal.objects.filter(
            restaurant__city=obj,
            restaurant__is_active=True,
            restaurant__verified=True,
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).count()


class RestaurantCategorySerializer(serializers.ModelSerializer):
    restaurants_count = serializers.SerializerMethodField()
    
    class Meta:
        model = RestaurantCategory
        fields = ("id", "name", "slug", "icon", "restaurants_count", "created_at")
        
    def get_restaurants_count(self, obj):
        return obj.restaurants.filter(is_active=True, verified=True).count()


class FacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = ("id", "name", "slug", "icon", "is_active")


class RestaurantImageSerializer(ProcessedImageOutputMixin, serializers.ModelSerializer):
    class Meta:
        model = RestaurantImage
        fields = (
            "id",
            "image",
            "alt_text",
            "image_type",
            "is_primary",
            "order",
        )
        extra_kwargs = {
            "image": {"write_only": True, "required": False},
        }


class CuisineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cuisine
        fields = ("id", "name", "icon")


class HomeScreenCuisineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cuisine
        fields = ("id", "name", "icon")


class HomeScreenCuisineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cuisine
        fields = ("id", "name", "icon")




class RestaurantSerializer(serializers.ModelSerializer):
    city = CitySerializer(read_only=True)
    city_id = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.filter(is_active=True),
        source='city',
        write_only=True,
        required=True,
        help_text="ID of the city where the restaurant is located"
    )
    categories = RestaurantCategorySerializer(many=True, read_only=True)
    category_ids = serializers.PrimaryKeyRelatedField(
        queryset=RestaurantCategory.objects.all(),
        source='categories',
        many=True,
        write_only=True,
        required=False,
        help_text="List of category IDs"
    )
    cuisines = CuisineSerializer(many=True, read_only=True)
    cuisine_ids = serializers.PrimaryKeyRelatedField(
        queryset=Cuisine.objects.all(),
        source='cuisines',
        many=True,
        write_only=True,
        required=False,
        help_text="List of cuisine IDs"
    )
    images = RestaurantImageSerializer(many=True, read_only=True)
    facilities = FacilitySerializer(many=True, read_only=True)
    facility_ids = serializers.PrimaryKeyRelatedField(
        queryset=Facility.objects.all(),
        source='facilities',
        many=True,
        write_only=True,
        required=False,
        help_text="List of facility IDs"
    )
    active_deals_count = serializers.IntegerField(read_only=True)
    is_saved = serializers.SerializerMethodField()
    is_favourite = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = (
            "id", "name", "slug", "description", "city", "city_id", "address", "postcode",
            "latitude", "longitude", "phone", "email", "website", "category_ids", "categories",
            "cuisine_ids", "cuisines", "facility_ids",
            "price_range", "occupancy", "verified", "is_featured", "opening_hours",
            "menu_type", "images", "active_deals_count", "is_saved", "is_favourite", "facilities",
            "loyalty_card_enabled", "loyalty_required_redemptions", "loyalty_reward_description",
            "bookings_enabled", "created_at"
        )
        read_only_fields = ("slug", "verified", "is_featured", "created_at", "city", "categories", "cuisines", "images")

    def validate(self, attrs):
        loyalty_enabled = attrs.get(
            "loyalty_card_enabled",
            getattr(self.instance, "loyalty_card_enabled", False) if self.instance else False,
        )
        required = attrs.get(
            "loyalty_required_redemptions",
            getattr(self.instance, "loyalty_required_redemptions", None) if self.instance else None,
        )
        reward_desc = attrs.get(
            "loyalty_reward_description",
            getattr(self.instance, "loyalty_reward_description", "") if self.instance else "",
        )

        if loyalty_enabled:
            if not required or required < 1:
                raise serializers.ValidationError(
                    {"loyalty_required_redemptions": "Required when loyalty card is enabled (minimum 1)."}
                )
            if not reward_desc or not str(reward_desc).strip():
                raise serializers.ValidationError(
                    {"loyalty_reward_description": "Required when loyalty card is enabled."}
                )
        elif "loyalty_card_enabled" in attrs and not loyalty_enabled:
            attrs["loyalty_required_redemptions"] = None
            attrs["loyalty_reward_description"] = ""

        return attrs
        
    def get_is_saved(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return SavedRestaurant.objects.filter(user=request.user, restaurant=obj).exists()
        return False
    
    def get_is_favourite(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return SavedRestaurant.objects.filter(user=request.user, restaurant=obj).exists()
        return False

    
    def create(self, validated_data):
        # Auto-generate slug from name if not provided
        if 'slug' not in validated_data or not validated_data.get('slug'):
            from django.utils.text import slugify
            name = validated_data.get('name', '')
            base_slug = slugify(name)
            slug = base_slug
            counter = 1
            while Restaurant.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            validated_data['slug'] = slug
        
        # Handle categories if provided
        categories = validated_data.pop('categories', [])
        cuisines = validated_data.pop('cuisines', [])
        facilities = validated_data.pop('facilities', [])
        restaurant = Restaurant.objects.create(**validated_data)
        
        if categories:
            restaurant.categories.set(categories)
        if cuisines:
            restaurant.cuisines.set(cuisines)
        if facilities:
            restaurant.facilities.set(facilities)
        
        if restaurant.opening_hours:
            sync_opening_slots_from_opening_hours(restaurant)
        
        return restaurant
    
    def update(self, instance, validated_data):
        opening_hours_updated = "opening_hours" in validated_data
        # Handle categories if provided
        categories = validated_data.pop('categories', None)
        cuisines = validated_data.pop('cuisines', None)
        facilities = validated_data.pop('facilities', None)
        
        # Auto-update slug if name changed
        if 'name' in validated_data and validated_data['name'] != instance.name:
            from django.utils.text import slugify
            name = validated_data['name']
            base_slug = slugify(name)
            slug = base_slug
            counter = 1
            while Restaurant.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            validated_data['slug'] = slug
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if categories is not None:
            instance.categories.set(categories)
        if cuisines is not None:
            instance.cuisines.set(cuisines)
        if facilities is not None:
            instance.facilities.set(facilities)
        
        if opening_hours_updated:
            sync_opening_slots_from_opening_hours(instance)
        
        return instance


class RestaurantListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""
    city_name = serializers.CharField(source="city.name", read_only=True)
    country_name = serializers.CharField(source="city.country.name", read_only=True)
    primary_image = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    active_deals_count = serializers.IntegerField(read_only=True)
    claims_count = serializers.IntegerField(read_only=True, required=False, default=0)
    leaderboard_score = serializers.SerializerMethodField()
    distance_miles = serializers.SerializerMethodField()
    is_favourite = serializers.SerializerMethodField()
    active_deals = serializers.SerializerMethodField()
    cuisines = CuisineSerializer(many=True, read_only=True)
    facilities = FacilitySerializer(many=True, read_only=True)
    categories = RestaurantCategorySerializer(many=True, read_only=True)

    
    class Meta:
        model = Restaurant
        fields = (
            "id", "name", "slug", "description", "city_name", "country_name",
            "latitude", "longitude", "price_range", "occupancy", "verified",
            "is_featured", "primary_image", "average_rating", "review_count",
            "active_deals_count", "claims_count", "leaderboard_score", "distance_miles", "facilities", "categories",
            "is_favourite", "active_deals", "cuisines", "loyalty_card_enabled", "bookings_enabled"
        )

        
    def get_is_favourite(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return SavedRestaurant.objects.filter(user=request.user, restaurant=obj).exists()
        return False
        
    def get_primary_image(self, obj):
        return _get_primary_restaurant_image_url(obj, self.context.get("request"))

    def get_leaderboard_score(self, obj):
        return obj.get_leaderboard_score()

    def get_average_rating(self, obj):
        # 1. Try to use annotated value (preferred for performance)
        val = getattr(obj, "average_rating", None)
        if val is not None:
            return round(float(val), 1)
        
        # 2. Fallback to model method
        return round(obj.get_average_rating(), 1) or 0.0

    def get_review_count(self, obj):
        # 1. Try to use annotated value
        val = getattr(obj, "reviews_count", None)
        if val is not None:
            return int(val)
            
        # 2. Fallback to model method
        return obj.get_reviews_count() or 0

    def get_distance_miles(self, obj):
        # Check pre-calculated miles or convert from pre-calculated km
        value = getattr(obj, "_distance_miles", None)
        if value is None:
            dist_km = getattr(obj, "_distance", None)
            if dist_km is not None:
                from .services import km_to_miles
                value = km_to_miles(dist_km)
                
        return round(value, 2) if isinstance(value, (int, float)) else None

    def get_active_deals(self, obj):
        from django.utils import timezone
        now = timezone.now()
        active_deals = obj.deals.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        )
        return DealListSerializer(active_deals, many=True, context=self.context).data



class DealImageSerializer(ProcessedImageOutputMixin, serializers.ModelSerializer):
    class Meta:
        model = DealImage
        fields = (
            "id",
            "image",
            "alt_text",
            "is_primary",
            "order",
        )
        extra_kwargs = {
            "image": {"write_only": True, "required": False},
        }


class DealSerializer(serializers.ModelSerializer):
    restaurant = RestaurantListSerializer(read_only=True)
    images = DealImageSerializer(many=True, read_only=True)
    is_active = serializers.SerializerMethodField()
    can_use = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()
    
    class Meta:
        model = Deal
        fields = (
            "id", "restaurant", "title", "description", "short_description", "deal_type",
            "discount_percentage", "discount_amount", "combo_price", "minimum_spend",
            "terms_and_conditions", "start_date", "end_date",
            "max_uses", "used_count", "max_per_user", "is_featured",
            "images", "is_active", "can_use", "is_saved", "created_at"
        )
        
    def get_is_active(self, obj):
        return obj.is_active_now()
    
    def get_can_use(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.can_user_use(request.user)
        return False
    
    def get_is_saved(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return SavedDeal.objects.filter(user=request.user, deal=obj).exists()
        return False


class DealListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for deal lists"""
    restaurant_id = serializers.IntegerField(read_only=True)
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    restaurant_slug = serializers.CharField(source="restaurant.slug", read_only=True)
    city_name = serializers.CharField(source="restaurant.city.name", read_only=True)
    latitude = serializers.FloatField(source="restaurant.latitude", read_only=True)
    longitude = serializers.FloatField(source="restaurant.longitude", read_only=True)
    distance_miles = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    
    class Meta:
        model = Deal
        fields = (
            "id", "restaurant_id", "title", "description", "short_description", "deal_type", "restaurant_name",
            "restaurant_slug", "city_name", "discount_percentage",
            "discount_amount", "combo_price", "minimum_spend", "terms_and_conditions",
            "start_date", "end_date", "max_per_user", "latitude", "longitude", "distance_miles",
            "is_featured", "primary_image", "is_active", "created_at"
        )
        
    def get_distance_miles(self, obj):
        return getattr(obj.restaurant, "_distance_miles", None) or getattr(obj, "_distance_miles", None)

    def get_primary_image(self, obj):
        return _get_primary_deal_image_url(obj, self.context.get("request"))

    def get_is_active(self, obj):
        return obj.is_active_now()


class DealToggleStatusSerializer(serializers.Serializer):
    """Serializer for toggling deal status with optional date updates"""
    start_date = serializers.DateTimeField(required=False, allow_null=True)
    end_date = serializers.DateTimeField(required=False, allow_null=True)
    
    def validate(self, data):
        from django.utils import timezone
        
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date and end_date:
            if start_date >= end_date:
                raise serializers.ValidationError(
                    "Start date must be before end date."
                )
            if end_date <= timezone.now():
                raise serializers.ValidationError(
                    "End date must be in the future."
                )
        elif start_date and not end_date:
            if start_date <= timezone.now():
                raise serializers.ValidationError(
                    "Start date must be in the future."
                )
        elif end_date and not start_date:
            if end_date <= timezone.now():
                raise serializers.ValidationError(
                    "End date must be in the future."
                )
        
        return data


class HomeScreenDealSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="deal_type")

    class Meta:
        model = Deal
        fields = (
            "id", "title", "short_description", "type", "discount_percentage", "combo_price",
            "minimum_spend", "start_date", "end_date", "restaurant_id"
        )


class SavedRestaurantSerializer(serializers.ModelSerializer):
    restaurant = RestaurantListSerializer(read_only=True)
    
    class Meta:
        model = SavedRestaurant
        fields = ("id", "restaurant", "created_at")


class SavedDealSerializer(serializers.ModelSerializer):
    deal = DealListSerializer(read_only=True)
    
    class Meta:
        model = SavedDeal
        fields = ("id", "deal", "created_at")


class DealUseSerializer(serializers.ModelSerializer):
    restaurant = serializers.SerializerMethodField()
    restaurant_name = serializers.SerializerMethodField()
    deal = DealListSerializer(read_only=True, allow_null=True)
    qr_code_url = serializers.SerializerMethodField()

    class Meta:
        model = DealUse
        fields = (
            "id",
            "restaurant",
            "restaurant_name",
            "deal",
            "is_loyalty_only",
            "used_at",
            "restaurant_confirmed",
            "notes",
            "redemption_code",
            "qr_code",
            "qr_code_url",
            "is_redeemed",
            "redeemed_at",
            "price",
            "people_count",
            "discount_amount_saved",
            "final_bill_amount",
            "created_at",
        )
        read_only_fields = (
            "redemption_code",
            "qr_code",
            "qr_code_url",
            "is_redeemed",
            "redeemed_at",
        )

    def _resolve_restaurant(self, obj):
        if obj.restaurant_id:
            return obj.restaurant
        if obj.deal_id and obj.deal:
            return obj.deal.restaurant
        return None

    def get_restaurant(self, obj):
        restaurant = self._resolve_restaurant(obj)
        return restaurant.id if restaurant else None

    def get_restaurant_name(self, obj):
        restaurant = self._resolve_restaurant(obj)
        return restaurant.name if restaurant else None

    def get_qr_code_url(self, obj):
        if not obj.qr_code:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.qr_code.url)
        return obj.qr_code.url


class DealUseCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating deal uses"""
    
    class Meta:
        model = DealUse
        fields = ("deal", "notes")
        
    def validate_deal(self, value):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            if not value.is_active_now():
                raise serializers.ValidationError("This deal is not currently active.")
            if not value.can_user_use(request.user):
                raise serializers.ValidationError("You have reached the maximum uses for this deal.")
        return value
    
    def create(self, validated_data):
        """
        Delegate creation to the service layer so that redemption code and QR
        generation (and used_count increment) are handled in one place.
        """
        from .services import create_deal_use_with_redemption

        user = self.context["request"].user
        deal = validated_data["deal"]
        notes = validated_data.get("notes", "")

        return create_deal_use_with_redemption(user=user, deal=deal, notes=notes)


class LoyaltyOnlyUseCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating loyalty-only deal uses"""
    
    class Meta:
        model = DealUse
        fields = ("restaurant", "notes")
        
    def validate_restaurant(self, value):
        if not value.loyalty_card_enabled or not value.loyalty_required_redemptions:
            raise serializers.ValidationError("Loyalty card is not enabled or configured for this restaurant.")
        return value
    
    def create(self, validated_data):
        from .services import create_deal_use_with_redemption

        user = self.context["request"].user
        restaurant = validated_data["restaurant"]
        notes = validated_data.get("notes", "")

        return create_deal_use_with_redemption(
            user=user, 
            restaurant=restaurant, 
            is_loyalty_only=True, 
            notes=notes
        )


# New serializers for mobile app features



class ReviewSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    user_name = serializers.SerializerMethodField()
    user_profile_picture = serializers.SerializerMethodField()
    
    class Meta:
        model = Review
        fields = (
            "id", "user", "user_email", "user_name", "user_profile_picture", "restaurant",
            "rating", "comment", "is_verified", "created_at"
        )
        read_only_fields = ("user", "is_verified")
        
    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username or obj.user.email.split('@')[0]
    
    def get_user_profile_picture(self, obj):
        try:
            profile = obj.user.profile
            if profile.profile_picture:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(profile.profile_picture.url)
                return profile.profile_picture.url
        except:
            pass
        return None
    
    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ReviewCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating reviews"""
    
    class Meta:
        model = Review
        fields = ("restaurant", "rating", "comment")
        
    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value
    
    def create(self, validated_data):
        user = self.context['request'].user
        restaurant = validated_data['restaurant']
        
        # Check if user already reviewed this restaurant
        review, created = Review.objects.get_or_create(
            user=user,
            restaurant=restaurant,
            defaults={
                'rating': validated_data['rating'],
                'comment': validated_data.get('comment', '')
            }
        )
        
        if not created:
            # Update existing review
            review.rating = validated_data['rating']
            review.comment = validated_data.get('comment', '')
            review.save()
        
        return review


class BookingSerializer(serializers.ModelSerializer):
    booking_id = serializers.IntegerField(source="id", read_only=True)
    restaurant_id = serializers.IntegerField(read_only=True)
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    restaurant_slug = serializers.CharField(source="restaurant.slug", read_only=True)
    restaurant_city_name = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = (
            "booking_id", "restaurant_id", "restaurant_name", "restaurant_slug", "restaurant_city_name",
            "booking_date", "number_of_guests", "status",
            "special_requests", "contact_phone", "contact_name",
            "arrived_time", "no_show_reason", "no_show_notes",
            "can_cancel", "created_at", "updated_at",
        )
        read_only_fields = ("user", "status")
        
    def get_can_cancel(self, obj):
        return obj.can_cancel()
    
    def get_restaurant_city_name(self, obj):
        return obj.restaurant.city.name if obj.restaurant and obj.restaurant.city else None

    
    def validate_number_of_guests(self, value):
        if value < 1:
            raise serializers.ValidationError("Number of guests must be at least 1.")
        return value
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class BookingCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating bookings"""
    booking_id = serializers.IntegerField(source="id", read_only=True)
    restaurant_id = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Booking
        fields = ("booking_id", "restaurant_id", "restaurant", "booking_date", "number_of_guests", "special_requests", "contact_phone", "contact_name")
        read_only_fields = ("booking_id", "restaurant_id")
        extra_kwargs = {
            'restaurant': {'write_only': True}
        }
        
    def validate_number_of_guests(self, value):
        if value < 1:
            raise serializers.ValidationError("Number of guests must be at least 1.")
        return value
    
    def validate_booking_date(self, value):
        from django.utils import timezone
        if value < timezone.now():
            raise serializers.ValidationError("Booking date cannot be in the past.")
        return value
    
    def create(self, validated_data):
        user = self.context['request'].user
        return Booking.objects.create(user=user, **validated_data)


class BookingManagementSerializer(BookingSerializer):
    """Serializer for merchants to manage bookings (allows status update)"""

    class Meta:
        model = Booking
        fields = BookingSerializer.Meta.fields
        read_only_fields = ("user",)


class MerchantBookingListSerializer(serializers.ModelSerializer):
    """Serializer for merchant calendar/list views."""

    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)

    class Meta:
        model = Booking
        fields = (
            "id",
            "restaurant_name",
            "contact_name",
            "contact_phone",
            "number_of_guests",
            "booking_date",
            "status",
            "arrived_time",
            "no_show_reason",
            "no_show_notes",
            "updated_at",
        )


class BookingArriveSerializer(serializers.Serializer):
    arrival_time = serializers.DateTimeField(required=False)

    def validate_arrival_time(self, value):
        if value and value > timezone.now():
            raise serializers.ValidationError("Arrival time cannot be in the future.")
        return value


class BookingNoShowSerializer(serializers.Serializer):
    no_show_reason = serializers.CharField(max_length=255)
    no_show_notes = serializers.CharField(required=False, allow_blank=True, default="")


class BookingArriveResponseSerializer(serializers.ModelSerializer):
    booking_id = serializers.IntegerField(source="id", read_only=True)

    class Meta:
        model = Booking
        fields = ("booking_id", "status", "arrived_time", "updated_at")


class BookingNoShowResponseSerializer(serializers.ModelSerializer):
    booking_id = serializers.IntegerField(source="id", read_only=True)

    class Meta:
        model = Booking
        fields = ("booking_id", "status", "no_show_reason", "no_show_notes", "updated_at")

class MenuItemSerializer(ProcessedImageOutputMixin, serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = (
            "id",
            "name",
            "description",
            "price",
            "is_vegetarian",
            "is_vegan",
            "is_gluten_free",
            "is_available",
            "image",
            "order",
            "category",
        )
        extra_kwargs = {
            "image": {"write_only": True, "required": False},
        }


class MenuItemCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating menu items"""
    
    class Meta:
        model = MenuItem
        fields = (
            "id", "category", "name", "description", "price", "is_vegetarian",
            "is_vegan", "is_gluten_free", "is_available", "image", "order"
        )
    
    def validate_category(self, value):
        # Validate that the category belongs to a restaurant owned by the user
        request = self.context.get("request")
        if request and request.user:
            user = request.user
            # Check ownership logic (similar to views)
            # This might be complex to put in serializer, can be done in view permission/perform_create
            pass
        return value


class MenuCategorySerializer(serializers.ModelSerializer):
    items = MenuItemSerializer(many=True, read_only=True)
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = MenuCategory
        fields = ("id", "name", "description", "order", "is_active", "items", "items_count")
        
    def get_items_count(self, obj):
        return obj.items.filter(is_available=True).count()


class OpeningSlotSerializer(serializers.ModelSerializer):
    day_name = serializers.CharField(source="get_day_of_week_display", read_only=True)
    
    class Meta:
        model = OpeningSlot
        fields = ("id", "day_of_week", "day_name", "opening_time", "closing_time", "is_closed")
        
    def validate(self, data):
        if not data.get('is_closed', False):
            opening = data.get('opening_time')
            closing = data.get('closing_time')
            if opening and closing and opening >= closing:
                raise serializers.ValidationError("Closing time must be after opening time.")
        return data


class RestaurantDetailSerializer(serializers.ModelSerializer):
    """Comprehensive serializer for restaurant detail view"""
    city = CitySerializer(read_only=True)
    categories = RestaurantCategorySerializer(many=True, read_only=True)
    cuisines = CuisineSerializer(many=True, read_only=True)
    images = RestaurantImageSerializer(many=True, read_only=True)
    reviews = serializers.SerializerMethodField()
    menu_categories = serializers.SerializerMethodField()
    opening_slots = OpeningSlotSerializer(many=True, read_only=True)
    facilities = FacilitySerializer(many=True, read_only=True)
    active_deals = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    is_open_now = serializers.SerializerMethodField()
    is_favourite = serializers.SerializerMethodField()
    has_user_reviewed = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()
    distance_miles = serializers.SerializerMethodField()
    loyalty_program = serializers.SerializerMethodField()
    active_deals_count = serializers.IntegerField(read_only=True, required=False, default=0)
    claims_count = serializers.IntegerField(read_only=True, required=False, default=0)
    
    class Meta:
        model = Restaurant
        fields = (
            "id", "name", "slug", "description", "city", "address", "postcode",
            "latitude", "longitude", "phone", "email", "website",
            "categories", "cuisines", "facilities", "price_range", "occupancy", "verified", "is_featured",
            "opening_hours", "images", "reviews", "menu_categories", "opening_slots",
            "active_deals", "active_deals_count", "claims_count", "average_rating", "reviews_count", "is_open_now",
            "is_favourite", "has_user_reviewed", "distance", "distance_miles", "menu_type",
            "loyalty_program", "bookings_enabled", "created_at"
        )
        
    def get_reviews(self, obj):
        reviews = obj.reviews.all()[:10]  # Limit to 10 most recent
        return ReviewSerializer(reviews, many=True, context=self.context).data
    
    def get_menu_categories(self, obj):
        categories = obj.menu_categories.filter(is_active=True).order_by("order", "name")
        return MenuCategorySerializer(categories, many=True, context=self.context).data
    
    def get_active_deals(self, obj):
        from django.utils import timezone
        now = timezone.now()
        deals = obj.deals.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        )[:10]  # Limit to 10 active deals
        return DealListSerializer(deals, many=True, context=self.context).data
    
    def get_average_rating(self, obj):
        return obj.get_average_rating()
    
    def get_reviews_count(self, obj):
        return obj.get_reviews_count()
    
    def get_is_open_now(self, obj):
        return obj.is_open_now()
    
    def get_is_favourite(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return SavedRestaurant.objects.filter(user=request.user, restaurant=obj).exists()
        return False
        
    def get_has_user_reviewed(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.reviews.filter(user=request.user).exists()
        return False
    
    def get_distance(self, obj):
        # 1. Check if KM distance is pre-calculated
        dist_km = getattr(obj, '_distance', None)
        if dist_km is not None:
            return round(dist_km, 2)
        
        # 2. Try to get it from pre-calculated miles
        dist_miles = getattr(obj, '_distance_miles', None)
        if dist_miles is not None:
            return round(dist_miles * 1.60934, 2)
        return None

    def get_distance_miles(self, obj):
        # 1. Check if it's already pre-calculated as miles
        value = getattr(obj, "_distance_miles", None)
        
        # 2. Check if it's pre-calculated as km
        if value is None:
            dist_km = getattr(obj, "_distance", None)
            if dist_km is not None:
                from .services import km_to_miles
                value = km_to_miles(dist_km)
        
        return round(value, 2) if isinstance(value, (int, float)) else None

    def get_loyalty_program(self, obj):
        if not obj.loyalty_card_enabled:
            return {"loyalty_card_enabled": False}

        request = self.context.get("request")
        loyalty = None
        if request and request.user.is_authenticated:
            loyalty = UserRestaurantLoyalty.objects.filter(
                user=request.user, restaurant=obj
            ).first()

        progress = build_loyalty_progress_payload(restaurant=obj, loyalty=loyalty)
        return progress or {"loyalty_card_enabled": True}


class RestaurantProfileSerializer(serializers.ModelSerializer):
    restaurant = RestaurantSerializer(read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)
    
    class Meta:
        model = RestaurantProfile
        fields = ("id", "user", "user_email", "restaurant", "is_primary_owner", "created_at")
        read_only_fields = ("user", "restaurant")


class HomeScreenRestaurantSerializer(serializers.ModelSerializer):
    location = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()
    distance_miles = serializers.SerializerMethodField()
    cuisines = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    deals = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    is_favourite = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = (
            "id", "name", "slug", "description", "location", "price_range", "occupancy",
            "verified", "is_featured", "image", "rating", "average_rating", "review_count",
            "distance_km", "distance_miles", "cuisines", "deals", "is_favourite",
            "loyalty_card_enabled", "bookings_enabled"
        )

    def get_location(self, obj):
        return {
            "city": obj.city.name if obj.city else None,
            "country": obj.city.country.name if obj.city and obj.city.country else None,
            "lat": float(obj.latitude) if obj.latitude else None,
            "lng": float(obj.longitude) if obj.longitude else None
        }

    def get_rating(self, obj):
        return {
            "average": self.get_average_rating(obj),
            "count": self.get_review_count(obj)
        }

    def get_average_rating(self, obj):
        return round(float(getattr(obj, 'average_rating', obj.get_average_rating()) or 0.0), 1)

    def get_review_count(self, obj):
        return getattr(obj, 'reviews_count', obj.get_reviews_count()) or 0

    def get_distance_km(self, obj):
        dist = getattr(obj, '_distance', None)
        if dist is None:
            dist_miles = getattr(obj, '_distance_miles', None)
            if dist_miles is not None:
                dist = dist_miles * 1.60934
        return round(float(dist), 2) if dist is not None else None

    def get_distance_miles(self, obj):
        dist_miles = getattr(obj, '_distance_miles', None)
        if dist_miles is None:
            dist_km = getattr(obj, '_distance', None)
            if dist_km is not None:
                dist_miles = float(dist_km) * 0.621371
        return round(float(dist_miles), 2) if dist_miles is not None else None

    def get_image(self, obj):
        return _get_primary_restaurant_image_url(obj, self.context.get("request"))

    def get_is_favourite(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return SavedRestaurant.objects.filter(user=request.user, restaurant=obj).exists()
        return False

    def get_deals(self, obj):
        from django.utils import timezone
        now = timezone.now()
        return list(obj.deals.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).values_list("id", flat=True))


class MysteryEvidenceSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = MysteryEvidence
        fields = ("id", "file", "file_url", "description", "created_at")
        read_only_fields = ("file_url", "created_at")

    def get_file_url(self, obj):
        if not obj.file:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url


class MysteryScoreSerializer(serializers.ModelSerializer):
    section_display = serializers.CharField(source="get_section_display", read_only=True)

    class Meta:
        model = MysteryScore
        fields = ("id", "section", "section_display", "score", "comment", "created_at")


class MysteryVisitSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    restaurant_city = serializers.CharField(source="restaurant.city.name", read_only=True)
    restaurant_slug = serializers.CharField(source="restaurant.slug", read_only=True)
    scores = MysteryScoreSerializer(many=True, read_only=True)
    evidence = MysteryEvidenceSerializer(many=True, read_only=True)

    class Meta:
        model = MysteryVisit
        fields = (
            "id",
            "restaurant",
            "restaurant_name",
            "restaurant_city",
            "restaurant_slug",
            "mystery_guest",
            "scheduled_for",
            "started_at",
            "submitted_at",
            "status",
            "overall_score",
            "is_risk_flagged",
            "comments",
            "scores",
            "evidence",
            "created_at",
        )
        read_only_fields = (
            "mystery_guest",
            "started_at",
            "submitted_at",
            "status",
            "overall_score",
            "created_at",
        )


class MysteryVisitSubmitSerializer(serializers.Serializer):
    """
    Payload for submitting a completed mystery visit evaluation.

    All core questionnaire sections are required and scored 0–10.
    """

    pre_visit_score = serializers.IntegerField(min_value=0, max_value=10)
    ambience_score = serializers.IntegerField(min_value=0, max_value=10)
    service_score = serializers.IntegerField(min_value=0, max_value=10)
    food_score = serializers.IntegerField(min_value=0, max_value=10)
    discount_experience_score = serializers.IntegerField(min_value=0, max_value=10)
    hygiene_score = serializers.IntegerField(min_value=0, max_value=10)

    pre_visit_comment = serializers.CharField(required=False, allow_blank=True)
    ambience_comment = serializers.CharField(required=False, allow_blank=True)
    service_comment = serializers.CharField(required=False, allow_blank=True)
    food_comment = serializers.CharField(required=False, allow_blank=True)
    discount_experience_comment = serializers.CharField(required=False, allow_blank=True)
    hygiene_comment = serializers.CharField(required=False, allow_blank=True)

    is_risk_flagged = serializers.BooleanField(required=False, default=False)
    comments = serializers.CharField(required=False, allow_blank=True)


class DealRedemptionRequestSerializer(serializers.Serializer):
    """
    Request payload for redeeming a deal at the restaurant.

    Either redemption_code (6-digit code) or qr_data (raw QR payload string)
    must be provided.
    """

    redemption_code = serializers.CharField(max_length=6, required=False)
    qr_data = serializers.CharField(required=False)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    people_count = serializers.IntegerField(min_value=1, required=True)
    restaurant_id = serializers.IntegerField(required=False)

    def validate(self, attrs):
        redemption_code = attrs.get("redemption_code")
        qr_data = attrs.get("qr_data")
        if not redemption_code and not qr_data:
            raise serializers.ValidationError("Either redemption_code or qr_data is required.")
        return attrs

class RestaurantPartnerRequestSerializer(serializers.ModelSerializer):
    """Serializer for 'Join as Restaurant Partner' form"""
    class Meta:
        model = RestaurantPartnerRequest
        fields = (
            "id", "restaurant_name", "contact_name", "email", "phone",
            "city_name", "website", "comments", "status", "created_at"
        )
        read_only_fields = ("id", "status", "created_at")
        extra_kwargs = {
            "website": {"required": False, "allow_null": True, "allow_blank": True},
            "comments": {"required": False, "allow_null": True, "allow_blank": True},
        }


class LoyaltyProgressSerializer(serializers.Serializer):
    """Customer loyalty progress for a single restaurant."""
    loyalty_card_enabled = serializers.BooleanField()
    required_redemptions = serializers.IntegerField(required=False)
    reward_description = serializers.CharField(required=False, allow_blank=True)
    completed_redemptions = serializers.IntegerField(required=False)
    remaining_redemptions = serializers.IntegerField(required=False)
    progress_text = serializers.CharField(required=False, allow_blank=True)
    progress_percentage = serializers.FloatField(required=False)
    is_reward_eligible = serializers.BooleanField(required=False)
    reward_eligible_at = serializers.DateTimeField(required=False, allow_null=True)
    total_lifetime_redemptions = serializers.IntegerField(required=False)
    rewards_earned = serializers.IntegerField(required=False)
    last_reward_claimed_at = serializers.DateTimeField(required=False, allow_null=True)


class UserLoyaltyCardSerializer(serializers.ModelSerializer):
    """User's loyalty card summary across restaurants."""
    restaurant_id = serializers.IntegerField(source="restaurant.id", read_only=True)
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    restaurant_slug = serializers.CharField(source="restaurant.slug", read_only=True)
    restaurant_image = serializers.SerializerMethodField()
    reward_qr_url = serializers.SerializerMethodField()
    loyalty_program = serializers.SerializerMethodField()

    class Meta:
        model = UserRestaurantLoyalty
        fields = (
            "id", "restaurant_id", "restaurant_name", "restaurant_slug", "restaurant_image",
            "current_cycle_redemptions", "total_lifetime_redemptions", "rewards_earned",
            "is_reward_eligible", "reward_eligible_at", "reward_code", "reward_qr_url",
            "last_reward_claimed_at", "loyalty_program", "created_at", "updated_at",
        )

    def get_restaurant_image(self, obj):
        return _get_primary_restaurant_image_url(obj.restaurant, self.context.get("request"))

    def get_reward_qr_url(self, obj):
        if not obj.is_reward_eligible or not obj.reward_qr_code:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.reward_qr_code.url)
        return obj.reward_qr_code.url

    def get_loyalty_program(self, obj):
        return build_loyalty_progress_payload(restaurant=obj.restaurant, loyalty=obj)


class MerchantLoyaltyCustomerSerializer(serializers.ModelSerializer):
    """Merchant view of a customer's loyalty status."""
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.SerializerMethodField()
    loyalty_program = serializers.SerializerMethodField()

    class Meta:
        model = UserRestaurantLoyalty
        fields = (
            "id", "user_id", "user_email", "user_name",
            "current_cycle_redemptions", "total_lifetime_redemptions", "rewards_earned",
            "is_reward_eligible", "reward_eligible_at", "last_reward_claimed_at",
            "loyalty_program", "updated_at",
        )

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.email

    def get_loyalty_program(self, obj):
        return build_loyalty_progress_payload(restaurant=obj.restaurant, loyalty=obj)


class LoyaltyRedemptionRecordSerializer(serializers.ModelSerializer):
    """Audit record for loyalty redemption history."""
    user_email = serializers.EmailField(source="user.email", read_only=True)
    deal_use_id = serializers.IntegerField(source="deal_use.id", read_only=True, allow_null=True)
    deal_title = serializers.CharField(source="deal_use.deal.title", read_only=True, allow_null=True)

    class Meta:
        model = LoyaltyRedemptionRecord
        fields = (
            "id", "user_email", "deal_use_id", "deal_title", "status",
            "cycle_redemption_number", "total_lifetime_redemptions", "notes", "created_at",
        )


class LoyaltyRewardClaimSerializer(serializers.Serializer):
    """Request body for merchant to mark a loyalty reward as claimed."""
    restaurant_id = serializers.IntegerField()
    user_id = serializers.IntegerField()

    def validate_restaurant_id(self, value):
        if not Restaurant.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError("Restaurant not found.")
        return value

    def validate_user_id(self, value):
        from users.models import User
        if not User.objects.filter(pk=value).exists():
            raise serializers.ValidationError("User not found.")
        return value

