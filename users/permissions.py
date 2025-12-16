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


