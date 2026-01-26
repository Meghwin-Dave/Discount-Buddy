from rest_framework import serializers

from .models import (
    Country, City, RestaurantCategory, Restaurant, Deal,
    RestaurantImage, DealImage, SavedRestaurant, SavedDeal, DealUse,
    Cuisine, Review, Booking, MenuCategory, MenuItem, OpeningSlot, RestaurantProfile
)


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


class RestaurantImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = RestaurantImage
        fields = ("id", "image", "image_url", "alt_text", "is_primary", "order")
        
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class RestaurantSerializer(serializers.ModelSerializer):
    city = CitySerializer(read_only=True)
    categories = RestaurantCategorySerializer(many=True, read_only=True)
    images = RestaurantImageSerializer(many=True, read_only=True)
    active_deals_count = serializers.IntegerField(read_only=True)
    is_saved = serializers.SerializerMethodField()
    
    class Meta:
        model = Restaurant
        fields = (
            "id", "name", "slug", "description", "city", "address", "postcode",
            "latitude", "longitude", "phone", "email", "website", "categories",
            "price_range", "verified", "is_featured", "opening_hours",
            "images", "active_deals_count", "is_saved", "created_at"
        )
        
    def get_is_saved(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return SavedRestaurant.objects.filter(user=request.user, restaurant=obj).exists()
        return False


class RestaurantListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""
    city_name = serializers.CharField(source="city.name", read_only=True)
    country_name = serializers.CharField(source="city.country.name", read_only=True)
    primary_image = serializers.SerializerMethodField()
    active_deals_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Restaurant
        fields = (
            "id", "name", "slug", "city_name", "country_name",
            "latitude", "longitude", "price_range", "verified",
            "is_featured", "primary_image", "active_deals_count"
        )
        
    def get_primary_image(self, obj):
        primary_img = obj.images.filter(is_primary=True).first()
        if not primary_img:
            primary_img = obj.images.first()
        if primary_img and primary_img.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(primary_img.image.url)
            return primary_img.image.url
        return None


class DealImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = DealImage
        fields = ("id", "image", "image_url", "alt_text", "is_primary", "order")
        
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class DealSerializer(serializers.ModelSerializer):
    restaurant = RestaurantListSerializer(read_only=True)
    images = DealImageSerializer(many=True, read_only=True)
    is_active = serializers.SerializerMethodField()
    can_use = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()
    
    class Meta:
        model = Deal
        fields = (
            "id", "restaurant", "title", "description", "deal_type",
            "discount_percentage", "discount_amount", "minimum_spend",
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
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    restaurant_slug = serializers.CharField(source="restaurant.slug", read_only=True)
    city_name = serializers.CharField(source="restaurant.city.name", read_only=True)
    primary_image = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    
    class Meta:
        model = Deal
        fields = (
            "id", "title", "description", "deal_type", "restaurant_name",
            "restaurant_slug", "city_name", "discount_percentage",
            "discount_amount", "minimum_spend", "start_date", "end_date",
            "is_featured", "primary_image", "is_active", "created_at"
        )
        
    def get_primary_image(self, obj):
        primary_img = obj.images.filter(is_primary=True).first()
        if not primary_img:
            primary_img = obj.images.first()
        if primary_img and primary_img.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(primary_img.image.url)
            return primary_img.image.url
        return None
    
    def get_is_active(self, obj):
        return obj.is_active_now()


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
    deal = DealListSerializer(read_only=True)
    
    class Meta:
        model = DealUse
        fields = (
            "id", "deal", "used_at", "restaurant_confirmed",
            "notes", "created_at"
        )


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
        user = self.context["request"].user
        deal = validated_data["deal"]
        
        # Create the use record
        deal_use = DealUse.objects.create(
            user=user,
            deal=deal,
            notes=validated_data.get("notes", "")
        )
        
        # Increment used count
        deal.used_count += 1
        deal.save(update_fields=["used_count"])
        
        return deal_use


# New serializers for mobile app features
class CuisineSerializer(serializers.ModelSerializer):
    restaurants_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Cuisine
        fields = ("id", "name", "slug", "icon", "is_active", "restaurants_count", "created_at")
        
    def get_restaurants_count(self, obj):
        return obj.restaurants.filter(is_active=True, verified=True).count()


class ReviewSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Review
        fields = (
            "id", "user", "user_email", "user_name", "restaurant",
            "rating", "comment", "is_verified", "created_at"
        )
        read_only_fields = ("user", "is_verified")
        
    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username or obj.user.email.split('@')[0]
    
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
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    restaurant_slug = serializers.CharField(source="restaurant.slug", read_only=True)
    can_cancel = serializers.SerializerMethodField()
    
    class Meta:
        model = Booking
        fields = (
            "id", "restaurant", "restaurant_name", "restaurant_slug",
            "booking_date", "number_of_guests", "status",
            "special_requests", "contact_phone", "contact_name",
            "can_cancel", "created_at"
        )
        read_only_fields = ("user", "status")
        
    def get_can_cancel(self, obj):
        return obj.can_cancel()
    
    def validate_number_of_guests(self, value):
        if value < 1:
            raise serializers.ValidationError("Number of guests must be at least 1.")
        return value
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class BookingCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating bookings"""
    
    class Meta:
        model = Booking
        fields = ("restaurant", "booking_date", "number_of_guests", "special_requests", "contact_phone", "contact_name")
        
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


class MenuItemSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = MenuItem
        fields = (
            "id", "name", "description", "price", "is_vegetarian",
            "is_vegan", "is_gluten_free", "is_available", "image",
            "image_url", "order"
        )
        
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


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
    active_deals = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    is_open_now = serializers.SerializerMethodField()
    is_favourite = serializers.SerializerMethodField()
    distance = serializers.SerializerMethodField()
    
    class Meta:
        model = Restaurant
        fields = (
            "id", "name", "slug", "description", "city", "address", "postcode",
            "latitude", "longitude", "phone", "email", "website",
            "categories", "cuisines", "price_range", "verified", "is_featured",
            "opening_hours", "images", "reviews", "menu_categories", "opening_slots",
            "active_deals", "average_rating", "reviews_count", "is_open_now",
            "is_favourite", "distance", "created_at"
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
    
    def get_distance(self, obj):
        # Distance will be calculated in the view if lat/lng provided
        return getattr(obj, '_distance', None)


class RestaurantProfileSerializer(serializers.ModelSerializer):
    restaurant = RestaurantSerializer(read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)
    
    class Meta:
        model = RestaurantProfile
        fields = ("id", "user", "user_email", "restaurant", "is_primary_owner", "created_at")
        read_only_fields = ("user", "restaurant")

