from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import UserProfile


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "profile", None)
            and request.user.profile.role == UserProfile.ROLE_ADMIN
        )


class IsMerchant(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "profile", None)
            and request.user.profile.role == UserProfile.ROLE_MERCHANT
        )


class IsCustomer(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "profile", None)
            and request.user.profile.role == UserProfile.ROLE_CUSTOMER
        )


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


# New permissions for mobile app roles
class IsUser(BasePermission):
    """
    Permission for regular app users (customers).
    Users can browse, search, add reviews, make bookings, claim deals.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        # Check if user has customer role or no specific merchant/restaurant profile
        try:
            profile = request.user.profile
            # User is a customer (regular app user)
            if profile.role == UserProfile.ROLE_CUSTOMER:
                return True
            # User is not a merchant (can be admin or customer)
            if profile.role != UserProfile.ROLE_MERCHANT:
                return True
        except UserProfile.DoesNotExist:
            # No profile means regular user
            return True
        return False


class IsRestaurant(BasePermission):
    """
    Permission for restaurant owners/managers.
    Restaurants can manage their profile, menus, opening slots, offers, view reviews & bookings.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        # Check if user has merchant role or restaurant profile
        try:
            profile = request.user.profile
            if profile.role == UserProfile.ROLE_MERCHANT:
                return True
            # Check if user has a restaurant profile
            if hasattr(request.user, 'restaurant_profile'):
                return True
        except UserProfile.DoesNotExist:
            pass
        return False


class IsRestaurantOwner(BasePermission):
    """
    Permission to check if user owns a specific restaurant.
    Use in views that need to verify ownership of a restaurant.
    """
    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        # Check if user is merchant and restaurant belongs to them
        try:
            profile = request.user.profile
            if profile.role == UserProfile.ROLE_MERCHANT:
                # Check if restaurant belongs to user's merchant account
                if hasattr(obj, 'merchant') and obj.merchant and hasattr(request.user, 'merchant'):
                    return obj.merchant == request.user.merchant
                # Check restaurant profile
                if hasattr(request.user, 'restaurant_profile'):
                    return request.user.restaurant_profile.restaurant == obj
        except UserProfile.DoesNotExist:
            pass
        return False


# New permissions for mobile app roles
class IsUser(BasePermission):
    """
    Permission for regular app users (customers).
    Users can browse, search, add reviews, make bookings, claim deals.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        # Check if user has customer role or no specific merchant/restaurant profile
        try:
            profile = request.user.profile
            # User is a customer (regular app user)
            if profile.role == UserProfile.ROLE_CUSTOMER:
                return True
            # User is not a merchant (can be admin or customer)
            if profile.role != UserProfile.ROLE_MERCHANT:
                return True
        except UserProfile.DoesNotExist:
            # No profile means regular user
            return True
        return False


class IsRestaurant(BasePermission):
    """
    Permission for restaurant owners/managers.
    Restaurants can manage their profile, menus, opening slots, offers, view reviews & bookings.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        # Check if user has merchant role or restaurant profile
        try:
            profile = request.user.profile
            if profile.role == UserProfile.ROLE_MERCHANT:
                return True
            # Check if user has a restaurant profile
            if hasattr(request.user, 'restaurant_profile'):
                return True
        except UserProfile.DoesNotExist:
            pass
        return False


class IsRestaurantOwner(BasePermission):
    """
    Permission to check if user owns a specific restaurant.
    Use in views that need to verify ownership of a restaurant.
    """
    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        # Check if user is merchant and restaurant belongs to them
        try:
            profile = request.user.profile
            if profile.role == UserProfile.ROLE_MERCHANT:
                # Check if restaurant belongs to user's merchant account
                if hasattr(obj, 'merchant') and obj.merchant and hasattr(request.user, 'merchant'):
                    return obj.merchant == request.user.merchant
                # Check restaurant profile
                if hasattr(request.user, 'restaurant_profile'):
                    return request.user.restaurant_profile.restaurant == obj
        except UserProfile.DoesNotExist:
            pass
        return False

