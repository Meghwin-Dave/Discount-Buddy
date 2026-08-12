from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from core.serializers_image import ProfilePictureOutputMixin
from .models import UserProfile, RegistrationOTP

User = get_user_model()


class UserProfileSerializer(ProfilePictureOutputMixin, serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = (
            "role",
            "phone_number",
            "profile_picture",
            "marketing_opt_in",
        )
        extra_kwargs = {
            "profile_picture": {"write_only": True, "required": False},
        }


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    loyalty_stats = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "email", "username", "first_name", "last_name", "is_merchant", "is_customer", "profile", "loyalty_stats")

    def get_loyalty_stats(self, obj):
        from restaurants.models import UserRestaurantLoyalty

        base_qs = UserRestaurantLoyalty.objects.filter(
            user=obj,
            restaurant__loyalty_card_enabled=True,
            restaurant__loyalty_required_redemptions__gt=0,
            restaurant__is_active=True,
        )
        active_qs = base_qs.filter(
            Q(current_cycle_redemptions__gt=0) | Q(is_reward_eligible=True)
        )

        return {
            "active_restaurants_count": active_qs.count(),
            "reward_eligible_count": active_qs.filter(is_reward_eligible=True).count(),
        }


class UserUpdateSerializer(serializers.ModelSerializer):
    profile_picture = serializers.ImageField(source='profile.profile_picture', required=False)
    phone_number = serializers.CharField(source='profile.phone_number', required=False)
    marketing_opt_in = serializers.BooleanField(source='profile.marketing_opt_in', required=False)

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "profile_picture", "phone_number", "marketing_opt_in")

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', None)
        
        # Update User fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update Profile fields
        if profile_data:
            profile, created = UserProfile.objects.get_or_create(user=instance)
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
            
        return instance



class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom serializer to add username, role, and current date to login response"""
    
    @classmethod
    def get_token(cls, user):
        """Add custom claims to the token payload"""
        token = super().get_token(user)
        
        # Add role to token payload
        try:
            token['role'] = user.profile.role
        except UserProfile.DoesNotExist:
            token['role'] = None

        if user.is_merchant:
            token['role'] = UserProfile.ROLE_MERCHANT
        
        # Add is_merchant and is_customer flags to token payload
        token['is_merchant'] = user.is_merchant
        token['is_customer'] = user.is_customer
        
        return token
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add username
        data['username'] = self.user.username
        
        # Add role from user profile
        try:
            data['role'] = self.user.profile.role
        except UserProfile.DoesNotExist:
            data['role'] = None

        if self.user.is_merchant:
            data['role'] = UserProfile.ROLE_MERCHANT
        
        # Add current date
        data['current_date'] = timezone.now().isoformat()
        
        return data


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(
        choices=UserProfile.ROLE_CHOICES, default=UserProfile.ROLE_CUSTOMER
    )

    class Meta:
        model = User
        fields = ("id", "email", "username", "password", "role")

    def create(self, validated_data):
        role = validated_data.pop("role", UserProfile.ROLE_CUSTOMER)
        password = validated_data.pop("password")
        user = User.objects.create(**validated_data)
        user.set_password(password)
        if role == UserProfile.ROLE_MERCHANT:
            user.is_merchant = True
            user.is_customer = False
        user.save()
        UserProfile.objects.get_or_create(user=user, defaults={"role": role})
        
        # Auto-create Merchant instance for merchant users
        if role == UserProfile.ROLE_MERCHANT:
            from vouchers.models import Merchant
            Merchant.objects.get_or_create(
                user=user,
                defaults={'name': user.username or user.email}
            )
        
        return user


class RegisterInitSerializer(serializers.Serializer):
    """Stage 1 of registration: collect email and desired role, send 4-digit OTP."""

    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=UserProfile.ROLE_CHOICES, default=UserProfile.ROLE_CUSTOMER)

    def validate_email(self, value):
        User = get_user_model()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value


class RegisterCompleteSerializer(serializers.Serializer):
    """
    Stage 3 of registration: finalize with password and optional username.
    
    Email, OTP, and password are required.
    Username is optional - if not provided, it will be derived from email.
    """

    email = serializers.EmailField()
    otp = serializers.CharField(max_length=4)
    password = serializers.CharField(write_only=True, min_length=6)
    username = serializers.CharField(max_length=30, required=False, allow_blank=True)

    def validate_username(self, value):
        """Validate username format if provided"""
        if not value:  # Optional field
            return value
        
        import re
        if not re.match(r"^[a-zA-Z0-9_-]{3,30}$", value):
            raise serializers.ValidationError(
                "Username must be 3-30 characters and contain only letters, numbers, underscores, or hyphens."
            )
        
        User = get_user_model()
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        
        return value



class VerifyOTPSerializer(serializers.Serializer):
    """
    Stage 2 of registration: verify the OTP.
    """

    email = serializers.EmailField()
    otp = serializers.CharField(max_length=4)


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer to request a password reset OTP.
    """

    email = serializers.EmailField()

    def validate_email(self, value):
        User = get_user_model()
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No user found with this email address.")
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer to confirm password reset using OTP.
    """

    email = serializers.EmailField()
    otp = serializers.CharField(max_length=4)
    password = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True, min_length=6)

    def validate(self, data):
        if data.get("password") != data.get("confirm_password"):
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return data

