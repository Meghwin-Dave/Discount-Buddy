from django.urls import path

from .views import (
    RegisterView,
    RegisterInitView,
    ResendOTPView,
    VerifyOTPView,
    RegisterCompleteView,
    CheckUsernameAvailabilityView,
    MeView,
    LoginView,
    RefreshTokenView,
    SocialLoginView,
    DeleteAccountInitView,
    DeleteAccountView,
    LogoutView,
    PasswordResetRequestView,
    PasswordResetVerifyOTPView,
    PasswordResetConfirmView,
)

urlpatterns = [
    # New two-stage registration flow
    path("register/init", RegisterInitView.as_view(), name="register-init"),
    path("register/resend-otp", ResendOTPView.as_view(), name="register-resend-otp"),
    path("register/verify-otp", VerifyOTPView.as_view(), name="register-verify-otp"),
    path("register/complete", RegisterCompleteView.as_view(), name="register-complete"),
    path("check-username", CheckUsernameAvailabilityView.as_view(), name="check-username"),

    # Legacy single-step registration (still available)
    path("register", RegisterView.as_view(), name="register"),
    path("login", LoginView.as_view(), name="login"),
    path("logout", LogoutView.as_view(), name="logout"),
    path("me", MeView.as_view(), name="me"),
    path("token", LoginView.as_view(), name="token_obtain_pair"),
    path("token/refresh", RefreshTokenView.as_view(), name="token_refresh"),
    path("oauth", SocialLoginView.as_view(), name="social_login"),
    path("account-delete/init", DeleteAccountInitView.as_view(), name="account-delete-init"),
    path("account-delete", DeleteAccountView.as_view(), name="account-delete"),
    path("password-reset/request", PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("password-reset/verify", PasswordResetVerifyOTPView.as_view(), name="password-reset-verify"),
    path("password-reset/confirm", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
]


