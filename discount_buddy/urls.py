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
    path("api/core/", include("core.urls")),
    path("api/users/", include("users.urls")),
    path("api/vouchers/", include("vouchers.urls")),
    path("api/wallet/", include("wallet.urls")),
    path("api/restaurants/", include("restaurants.urls")),
    # path("api/orders/", include("orders.urls")),
    # path("api/marketplace/", include("marketplace.urls")),
    path(
        "api/docs/swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path(
        "api/docs/redoc/",
        schema_view.with_ui("redoc", cache_timeout=0),
        name="schema-redoc",
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


