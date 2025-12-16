from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import UserProfile

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
        return user


