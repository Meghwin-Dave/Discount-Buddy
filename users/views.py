import random
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import UserProfile, RegistrationOTP
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    CustomTokenObtainPairSerializer,
    RegisterInitSerializer,
    RegisterCompleteSerializer,
    VerifyOTPSerializer,
    UserUpdateSerializer,
)

User = get_user_model()


class RegisterInitView(APIView):
    """
    Stage 1: accept email (and desired role) and send a 4-digit OTP.

    The email will later be used as the username as well.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = RegisterInitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        role = serializer.validated_data.get("role", UserProfile.ROLE_CUSTOMER)

        # Invalidate previous pending OTPs for this email.
        RegistrationOTP.objects.filter(email=email, is_verified=False).update(
            is_verified=True, verified_at=settings.TIME_ZONE and None
        )

        # Generate a 4-digit numeric OTP.
        otp_code = f"{random.randint(0, 9999):04d}"
        expires_at = timezone.now() + timedelta(minutes=10)

        RegistrationOTP.objects.create(
            email=email,
            role=role,
            otp_code=otp_code,
            expires_at=expires_at,
        )

        from_email = settings.DEFAULT_FROM_EMAIL
        subject = "Your Discount Buddy verification code"
        message = f"Your verification code is {otp_code}. It expires in 10 minutes."

        send_mail(subject, message, from_email, [email], fail_silently=False)

        return Response(
            {"detail": "Verification code sent to your email."},
            status=status.HTTP_200_OK,
        )


class VerifyOTPView(APIView):
    """
    Stage 2: verify OTP code.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        otp = serializer.validated_data["otp"]

        try:
            otp_obj = (
                RegistrationOTP.objects.filter(email=email, is_verified=False)
                .order_by("-created_at")
                .first()
            )
        except RegistrationOTP.DoesNotExist:
            otp_obj = None

        if not otp_obj:
            return Response(
                {"detail": "No pending verification code for this email."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if otp_obj.is_expired:
            return Response(
                {"detail": "Verification code has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if otp_obj.otp_code != otp:
            return Response(
                {"detail": "Invalid verification code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Mark OTP as verified (but not yet consumed by registration)
        otp_obj.is_verified = True
        otp_obj.verified_at = timezone.now()
        otp_obj.save(update_fields=["is_verified", "verified_at", "updated_at"])

        return Response(
            {"detail": "OTP verified successfully."},
            status=status.HTTP_200_OK,
        )


class RegisterCompleteView(APIView):
    """
    Stage 3: create the user with a password.
    Requires that the OTP has already been verified (or verifies it again here).
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = RegisterCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        otp = serializer.validated_data["otp"]
        password = serializer.validated_data["password"]

        User = get_user_model()
        if User.objects.filter(email=email).exists():
            return Response(
                {"detail": "A user with this email already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Look for a verified OTP that matches
        otp_obj = (
            RegistrationOTP.objects.filter(email=email, is_verified=True, otp_code=otp)
            .order_by("-verified_at")
            .first()
        )

        if not otp_obj:
            # Fallback: check if it's currently unverified but valid (for backward compatibility if someone skips verify-otp step)
            otp_obj = (
                RegistrationOTP.objects.filter(email=email, is_verified=False, otp_code=otp)
                .order_by("-created_at")
                .first()
            )
            
            if not otp_obj:
                return Response(
                    {"detail": "Verification code is invalid or has not been verified."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            if otp_obj.is_expired:
                 return Response(
                    {"detail": "Verification code has expired."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # If valid but not verified, mark it now
            otp_obj.is_verified = True
            otp_obj.verified_at = timezone.now()
            otp_obj.save(update_fields=["is_verified", "verified_at", "updated_at"])

        # Create the user
        role = otp_obj.role or UserProfile.ROLE_CUSTOMER
        username = email.split("@")[0] or email
        register_serializer = RegisterSerializer(
            data={
                "email": email,
                "username": username,
                "password": password,
                "role": role,
            }
        )
        register_serializer.is_valid(raise_exception=True)
        user = register_serializer.save()

        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class RegisterView(generics.CreateAPIView):
    """
    Existing single-step registration (email + password) kept for backward compatibility.

    Prefer using the new two-stage `/users/register/init` and `/users/register/complete`
    endpoints for production flows.
    """

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]
    serializer_class = CustomTokenObtainPairSerializer


class RefreshTokenView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]


class GoogleIdTokenLoginView(APIView):
    """
    Accept Google ID Token (from mobile or web client), verify it, and return JWT.
    POST body: { "id_token": "<google_id_token>" } or { "credential": "<google_id_token>" }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        id_token_str = (
            request.data.get("id_token")
            or request.data.get("credential")
            or (request.data.get("token") if isinstance(request.data.get("token"), str) else None)
        )
        if not id_token_str:
            return Response(
                {"detail": "id_token or credential is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        client_ids = getattr(settings, "GOOGLE_OAUTH_ALLOWED_CLIENT_IDS", [])
        if not client_ids:
            return Response(
                {"detail": "Google OAuth is not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        try:
            idinfo = id_token.verify_oauth2_token(
                id_token_str,
                google_requests.Request(),
                client_ids,
            )
        except ValueError as e:
            return Response(
                {"detail": f"Invalid Google ID token: {e!s}"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        email = idinfo.get("email")
        if not email:
            return Response(
                {"detail": "Google token did not contain email."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": email.split("@")[0] or email,
                "is_active": True,
            },
        )
        if created:
            user.set_unusable_password()
            user.save()
            UserProfile.objects.get_or_create(
                user=user,
                defaults={"role": UserProfile.ROLE_CUSTOMER},
            )
        refresh = RefreshToken.for_user(user)
        try:
            role = user.profile.role
        except UserProfile.DoesNotExist:
            role = None
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
                "username": user.username,
                "role": role,
                "is_merchant": user.is_merchant,
                "is_customer": user.is_customer,
            },
            status=status.HTTP_200_OK,
        )


