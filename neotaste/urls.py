from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    LoginView, VerifyOTPView,
    CityListView, SelectCityView,
    HomeView,
    RestaurantViewSet, OfferViewSet,
    WalletView, ProfileView, LogoutView
)

router = DefaultRouter()
router.register(r'restaurants', RestaurantViewSet, basename='restaurant')
router.register(r'offers', OfferViewSet, basename='offer')

urlpatterns = [
    # Authentication
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    
    # Cities
    path('cities/', CityListView.as_view(), name='cities'),
    path('user/select-city/', SelectCityView.as_view(), name='select-city'),
    
    # Home
    path('home/', HomeView.as_view(), name='home'),
    
    # Restaurants and Offers (via router)
    path('', include(router.urls)),
    
    # Wallet
    path('wallet/', WalletView.as_view(), name='wallet'),
    
    # Profile
    path('profile/', ProfileView.as_view(), name='profile'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
