from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import UserProfile, RegistrationOTP

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ("role", "phone_number", "marketing_opt_in")


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "username", "is_merchant", "is_customer", "profile")


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("username",)



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
        UserProfile.objects.create(user=user, role=role)
        
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
    Stage 2 of registration: verify OTP and set password.

    Username will be derived from the email's local part.
    """

    email = serializers.EmailField()
    otp = serializers.CharField(max_length=4)
    password = serializers.CharField(write_only=True, min_length=6)

