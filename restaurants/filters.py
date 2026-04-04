from django_filters import rest_framework as filters
from .models import Restaurant, Deal, City


class RestaurantFilter(filters.FilterSet):
    """Filter for restaurants"""
    min_price = filters.NumberFilter(field_name="price_range", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="price_range", lookup_expr="lte")
    has_deals = filters.BooleanFilter(method="filter_has_deals")
    city_slug = filters.CharFilter(field_name="city__slug", lookup_expr="exact")
    country_code = filters.CharFilter(field_name="city__country__code", lookup_expr="exact")
    
    day = filters.NumberFilter(method="filter_opening")
    time = filters.TimeFilter(method="filter_opening")
    
    class Meta:
        model = Restaurant
        fields = ["city", "verified", "is_featured", "categories", "cuisines", "price_range"]
    
    def filter_opening(self, queryset, name, value):
        if getattr(self, '_opening_filtered', False):
            return queryset
            
        self._opening_filtered = True
        
        day_val = self.data.get('day')
        time_val = self.data.get('time')
        
        if not day_val and not time_val:
            return queryset
        
        from .models import OpeningSlot
        from django.db.models import Q
        
        day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        final_q = Q()
        
        # 1. Filter using OpeningSlot model
        slot_filters = Q(is_closed=False)
        day_val_int = None
        if day_val is not None:
            try:
                day_val_int = int(day_val)
                slot_filters &= Q(day_of_week=day_val_int)
            except ValueError:
                pass
        if time_val is not None:
            slot_filters &= Q(opening_time__lte=time_val, closing_time__gte=time_val)
            
        open_restaurant_ids = OpeningSlot.objects.filter(slot_filters).values_list("restaurant_id", flat=True)
        final_q |= Q(id__in=open_restaurant_ids)
        
        # 2. Filter using opening_hours JSON field
        if day_val_int is not None and 0 <= day_val_int <= 6:
            day_name = day_names[day_val_int]
            # Check if the JSON field has the day_name key (not null)
            final_q |= Q(**{f"opening_hours__{day_name}__isnull": False})
            
        return queryset.filter(final_q).distinct()

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

