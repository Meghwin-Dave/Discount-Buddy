from django.urls import path

from .views import (
    RegisterView,
    RegisterInitView,
    VerifyOTPView,
    RegisterCompleteView,
    MeView,
    LoginView,
    RefreshTokenView,
    GoogleIdTokenLoginView,
)

urlpatterns = [
    # New two-stage registration flow
    path("register/init", RegisterInitView.as_view(), name="register-init"),
    path("register/verify-otp", VerifyOTPView.as_view(), name="register-verify-otp"),
    path("register/complete", RegisterCompleteView.as_view(), name="register-complete"),

    # Legacy single-step registration (still available)
    path("register", RegisterView.as_view(), name="register"),
    path("login", LoginView.as_view(), name="login"),
    path("me", MeView.as_view(), name="me"),
    path("token", LoginView.as_view(), name="token_obtain_pair"),
    path("token/refresh", RefreshTokenView.as_view(), name="token_refresh"),
    path("google", GoogleIdTokenLoginView.as_view(), name="google_id_token_login"),
]


