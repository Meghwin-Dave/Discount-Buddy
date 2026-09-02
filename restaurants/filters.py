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
        from django.db.models import F, Q
        
        slot_filters = Q(is_closed=False)
        if day_val is not None:
            try:
                slot_filters &= Q(day_of_week=int(day_val))
            except ValueError:
                pass

        if time_val is not None:
            # A slot covers the requested time in one of three ways: a normal
            # window containing it, an overnight window it falls either side of,
            # or an all-day window (identical open and close times).
            within_normal = Q(closing_time__gt=F("opening_time")) & Q(
                opening_time__lte=time_val, closing_time__gt=time_val
            )
            within_overnight = Q(closing_time__lt=F("opening_time")) & (
                Q(opening_time__lte=time_val) | Q(closing_time__gt=time_val)
            )
            open_all_day = Q(closing_time=F("opening_time"))
            slot_filters &= within_normal | within_overnight | open_all_day

        open_restaurant_ids = OpeningSlot.objects.filter(slot_filters).values_list(
            "restaurant_id", flat=True
        )
        return queryset.filter(id__in=open_restaurant_ids).distinct()

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

