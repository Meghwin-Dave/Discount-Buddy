from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from google.api_core.exceptions import GoogleAPIError
from google.auth.exceptions import DefaultCredentialsError, GoogleAuthError

from users.permissions import IsSuperUserOrAdmin
from core.services.analytics_dashboard import get_dashboard
from core.services.google_analytics import GoogleAnalyticsService


class AnalyticsDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUserOrAdmin]

    @swagger_auto_schema(
        tags=["Analytics"],
        operation_summary="Admin analytics dashboard",
        manual_parameters=[
            openapi.Parameter(
                "start_date",
                openapi.IN_QUERY,
                description="GA4 start (e.g. 7daysAgo, 30daysAgo, 20260101)",
                type=openapi.TYPE_STRING,
                default="30daysAgo",
            ),
            openapi.Parameter(
                "end_date",
                openapi.IN_QUERY,
                description="GA4 end (e.g. today)",
                type=openapi.TYPE_STRING,
                default="today",
            ),
        ],
    )
    def get(self, request):
        start_date = request.query_params.get("start_date", "30daysAgo")
        end_date = request.query_params.get("end_date", "today")
        try:
            data = get_dashboard(start_date=start_date, end_date=end_date)
        except ValueError as exc:
            message = str(exc)
            code = status.HTTP_503_SERVICE_UNAVAILABLE if "GA4_PROPERTY_ID" in message else status.HTTP_400_BAD_REQUEST
            return Response({"detail": message}, status=code)
        except (DefaultCredentialsError, GoogleAuthError) as exc:
            return Response({"detail": str(exc) or "GA4 credentials are not configured."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except GoogleAPIError as exc:
            return Response({"detail": str(exc) or "Google Analytics request failed."}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as exc:
            return Response({"detail": str(exc) or "Analytics is unavailable."}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(data)


class AnalyticsOverviewAPIView(APIView):
    permission_classes = [IsAuthenticated, IsSuperUserOrAdmin]

    def get(self, request):
        start_date = request.query_params.get("start_date", "7daysAgo")
        end_date = request.query_params.get("end_date", "today")
        try:
            analytics = GoogleAnalyticsService()
            data = analytics.get_overview(start_date=start_date, end_date=end_date)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except (DefaultCredentialsError, GoogleAuthError, GoogleAPIError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(data)
