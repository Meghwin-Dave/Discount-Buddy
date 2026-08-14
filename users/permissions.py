from rest_framework.permissions import BasePermission, SAFE_METHODS

from .merchant_utils import user_is_merchant
from .models import UserProfile


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.is_staff
                or (getattr(request.user, "profile", None) and request.user.profile.role == UserProfile.ROLE_ADMIN)
            )
        )


class IsSuperUserOrAdmin(BasePermission):
    """
    Permission class to allow access to superusers, staff users, or users with admin role.
    """
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.is_staff
                or (getattr(request.user, "profile", None) and request.user.profile.role == UserProfile.ROLE_ADMIN)
            )
        )


class IsMerchant(BasePermission):
    def has_permission(self, request, view):
        return user_is_merchant(request.user)


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


class IsUser(BasePermission):
    """
    Permission for regular app users (customers).
    Users can browse, search, add reviews, make bookings, claim deals.
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if user_is_merchant(request.user):
            return False
        try:
            profile = request.user.profile
            if profile.role == UserProfile.ROLE_CUSTOMER:
                return True
            if profile.role != UserProfile.ROLE_MERCHANT:
                return True
        except UserProfile.DoesNotExist:
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
        if user_is_merchant(request.user):
            return True
        if hasattr(request.user, "restaurant_profile"):
            return True
        return False


class IsRestaurantOwner(BasePermission):
    """
    Permission to check if user owns a specific restaurant.
    Use in views that need to verify ownership of a restaurant.
    """

    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        if user_is_merchant(request.user):
            if hasattr(obj, "merchant") and obj.merchant and hasattr(request.user, "merchant"):
                return obj.merchant == request.user.merchant
            if hasattr(request.user, "restaurant_profile"):
                return request.user.restaurant_profile.restaurant == obj
        if hasattr(request.user, "restaurant_profile"):
            return request.user.restaurant_profile.restaurant == obj
        return False


class IsMysteryGuest(BasePermission):
    """
    Permission for Mystery Guest evaluators.

    These users can access assigned restaurants, submit reports, and upload
    evidence but cannot modify restaurant data.
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        try:
            profile = request.user.profile
            return profile.role == UserProfile.ROLE_MYSTERY_GUEST
        except UserProfile.DoesNotExist:
            return False
