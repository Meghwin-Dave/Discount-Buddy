import random
from datetime import timedelta

import threading
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
import jwt
import requests
from jwt.algorithms import RSAAlgorithm

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

        # Send email asynchronously to improve response time
        def send_otp_email():
            try:
                send_mail(subject, message, from_email, [email], fail_silently=False)
            except Exception as e:
                # Log the error if possible
                pass

        threading.Thread(target=send_otp_email).start()

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


class SocialLoginView(APIView):
    """
    Unified OAuth login view for Google and Apple.
    POST body: { "provider": "google"/"apple", "token": "..." }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        provider = request.data.get("provider")
        token_str = (
            request.data.get("token")
            or request.data.get("id_token")
            or request.data.get("credential")
            or request.data.get("identityToken")
        )
        
        if not token_str:
            return Response(
                {"detail": "token, id_token, or credential is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Autodetect provider if not explicitly sent, for backward compatibility
        if not provider:
            if request.data.get("identityToken") or request.data.get("token") and not (request.data.get("id_token") or request.data.get("credential")):
                # This is a bit weak, but if token is passed and it's not and id_token/credential, 
                # we might assume apple if provider is missing. 
                # Better to require provider for the new endpoint.
                pass

        email = None
        
        if provider == "google" or not provider: # Default to google if provider missing for backward compatibility
            client_ids = getattr(settings, "GOOGLE_OAUTH_ALLOWED_CLIENT_IDS", [])
            if not client_ids:
                return Response(
                    {"detail": "Google OAuth is not configured."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            try:
                idinfo = id_token.verify_oauth2_token(
                    token_str,
                    google_requests.Request(),
                    client_ids,
                )
                email = idinfo.get("email")
            except Exception as e:
                if provider == "google":
                    return Response(
                        {"detail": f"Invalid Google token: {e!s}"},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                # If provider was auto-detected, we might try apple next? 
                # No, let's keep it simple: required provider for new logic.
        
        if (provider == "apple") or (not email and not provider):
            allowed_client_ids = getattr(settings, "APPLE_OAUTH_ALLOWED_CLIENT_IDS", ["com.ketan.discountbuddy"])
            try:
                response = requests.get("https://appleid.apple.com/auth/keys")
                apple_keys = response.json().get("keys", [])
                token_header = jwt.get_unverified_header(token_str)
                kid = token_header.get("kid")
                apple_key = next((k for k in apple_keys if k["kid"] == kid), None)
                if apple_key:
                    public_key = RSAAlgorithm.from_jwk(apple_key)
                    decoded_token = jwt.decode(
                        token_str,
                        public_key,
                        algorithms=["RS256"],
                        audience=allowed_client_ids,
                        issuer="https://appleid.apple.com",
                    )
                    email = decoded_token.get("email") or f"{decoded_token.get('sub')}@apple.com"
            except Exception as e:
                if provider == "apple":
                    return Response(
                        {"detail": f"Invalid Apple token: {e!s}"},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )

        if not email:
            return Response(
                {"detail": "Authentication failed or unsupported provider."},
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


class DeleteAccountInitView(APIView):
    """
    Step 1: Send OTP for account deletion.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        email = user.email

        # Invalidate previous pending OTPs for this email.
        RegistrationOTP.objects.filter(email=email, is_verified=False).update(
            is_verified=True, verified_at=timezone.now()
        )

        # Generate a 4-digit numeric OTP.
        otp_code = f"{random.randint(0, 9999):04d}"
        expires_at = timezone.now() + timedelta(minutes=10)

        RegistrationOTP.objects.create(
            email=email,
            otp_code=otp_code,
            expires_at=expires_at,
        )

        from_email = settings.DEFAULT_FROM_EMAIL
        subject = "Account Deletion OTP - Discount Buddy"
        message = f"Your verification code for account deletion is {otp_code}. It expires in 10 minutes. If you did not request this, please ignore this email."

        # Send email asynchronously to improve response time
        def send_otp_email():
            try:
                send_mail(subject, message, from_email, [email], fail_silently=False)
            except Exception:
                # Log the error if possible
                pass

        threading.Thread(target=send_otp_email).start()

        return Response(
            {"detail": "Verification code sent to your email."},
            status=status.HTTP_200_OK,
        )


class DeleteAccountView(APIView):
    """
    Step 2: Verify OTP and delete account.
    """

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        user = request.user
        otp = request.data.get("otp")

        if not otp:
            return Response(
                {"detail": "OTP is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp_obj = (
            RegistrationOTP.objects.filter(
                email=user.email, is_verified=False, otp_code=otp
            )
            .order_by("-created_at")
            .first()
        )

        if not otp_obj:
            return Response(
                {"detail": "Invalid or expired verification code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if otp_obj.is_expired:
            return Response(
                {"detail": "Verification code has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Mark OTP as verified
        otp_obj.is_verified = True
        otp_obj.verified_at = timezone.now()
        otp_obj.save()

        # Delete user
        user.delete()
        return Response(
            {"detail": "Account deleted successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )

class LogoutView(APIView):
    """
    Logout view that blacklists the refresh token to end the session.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response(
                    {"detail": "refresh token is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(
                {"detail": "Successfully logged out."},
                status=status.HTTP_200_OK,
            )
        except Exception:
            return Response(
                {"detail": "Invalid refresh token or token already blacklisted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
