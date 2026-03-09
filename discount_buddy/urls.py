from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Discount Buddy API",
        default_version="v1",
        description="API documentation for Discount Buddy platform",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # ===================== User-facing APIs =====================
    path("user/api/core/", include("core.urls")),
    path("user/api/users/", include("users.urls")),
    path("user/api/vouchers/", include("vouchers.user_urls")),
    path("user/api/wallet/", include("wallet.urls")),
    path("user/api/restaurants/", include("restaurants.user_urls")),
    path("user/api/notifications/", include("notifications.urls")),
    path("user/api/notifications", include("notifications.urls")),
    path("api/app/", include("configs.urls")),
    path("api/restaurants/", include("restaurants.user_urls")),

    # ===================== Merchant-facing APIs =====================
    path("merchant/api/core/", include("core.urls")),
    path("merchant/api/users/", include("users.urls")),
    path("merchant/api/vouchers/", include("vouchers.merchant_urls")),
    path("merchant/api/restaurants/", include("restaurants.merchant_urls")),
    path("merchant/api/notifications/", include("notifications.urls")),
    path("merchant/api/notifications", include("notifications.urls")),
    # path("api/orders/", include("orders.urls")),
    # path("api/marketplace/", include("marketplace.urls")),
    path(
        "user/api/docs/swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui-user",
    ),
    path(
        "user/api/docs/redoc/",
        schema_view.with_ui("redoc", cache_timeout=0),
        name="schema-redoc-user",
    ),
    path(
        "merchant/api/docs/swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui-merchant",
    ),
    path(
        "merchant/api/docs/redoc/",
        schema_view.with_ui("redoc", cache_timeout=0),
        name="schema-redoc-merchant",
    ),
]

# Serve static and media files in development
if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


