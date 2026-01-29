from django.conf import settings
from django.contrib.auth import get_user_model
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import UserProfile
from .serializers import RegisterSerializer, UserSerializer, CustomTokenObtainPairSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


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
        client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", None)
        if not client_id:
            return Response(
                {"detail": "Google OAuth is not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        try:
            idinfo = id_token.verify_oauth2_token(
                id_token_str,
                google_requests.Request(),
                client_id,
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


