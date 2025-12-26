from django_filters import rest_framework as filters
from .models import Restaurant, Deal, City


class RestaurantFilter(filters.FilterSet):
    """Filter for restaurants"""
    min_price = filters.NumberFilter(field_name="price_range", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="price_range", lookup_expr="lte")
    has_deals = filters.BooleanFilter(method="filter_has_deals")
    city_slug = filters.CharFilter(field_name="city__slug", lookup_expr="exact")
    country_code = filters.CharFilter(field_name="city__country__code", lookup_expr="exact")
    
    class Meta:
        model = Restaurant
        fields = ["city", "verified", "is_featured", "categories", "price_range"]
    
    def filter_has_deals(self, queryset, name, value):
        """Filter restaurants that have active deals"""
        from django.utils import timezone
        if value:
            now = timezone.now()
            return queryset.filter(
                deals__is_active=True,
                deals__start_date__lte=now,
                deals__end_date__gte=now
            ).distinct()
        return queryset


class DealFilter(filters.FilterSet):
    """Filter for deals"""
    city_slug = filters.CharFilter(field_name="restaurant__city__slug", lookup_expr="exact")
    country_code = filters.CharFilter(field_name="restaurant__city__country__code", lookup_expr="exact")
    restaurant_slug = filters.CharFilter(field_name="restaurant__slug", lookup_expr="exact")
    min_discount = filters.NumberFilter(field_name="discount_percentage", lookup_expr="gte")
    max_discount = filters.NumberFilter(field_name="discount_percentage", lookup_expr="lte")
    
    class Meta:
        model = Deal
        fields = ["restaurant", "deal_type", "is_featured"]

