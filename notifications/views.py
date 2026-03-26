"""
Notification API Views
Handles HTTP requests for notifications.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from .models import Notification, DeviceToken
from .serializers import NotificationSerializer, DeviceTokenSerializer
from .services import NotificationService


class NotificationPagination(PageNumberPagination):
    """Custom pagination for notifications"""
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for user notifications.
    
    Endpoints:
    - GET /api/v1/notifications/ - List notifications (paginated)
    - GET /api/v1/notifications/{id}/ - Get specific notification
    - GET /api/v1/notifications/unread-count/ - Get unread count
    - PATCH /api/v1/notifications/{id}/mark-read/ - Mark notification as read
    - PATCH /api/v1/notifications/read-all/ - Mark all as read
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = NotificationPagination

    def get_queryset(self):
        """Return notifications for the authenticated user only"""
        return Notification.objects.filter(user=self.request.user)

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        """
        Get count of unread notifications.
        
        GET /api/v1/notifications/unread-count/
        
        Returns:
            {"count": 5}
        """
        count = NotificationService.get_unread_count(request.user)
        return Response({"count": count})

    @action(detail=True, methods=["patch"])
    def mark_read(self, request, pk=None):
        """
        Mark a specific notification as read.
        
        PATCH /api/v1/notifications/{id}/mark-read/
        
        Returns:
            {"success": true, "message": "Notification marked as read"}
        """
        success = NotificationService.mark_as_read(pk, request.user)
        
        if success:
            return Response({
                "success": True,
                "message": "Notification marked as read"
            })
        else:
            return Response(
                {"success": False, "message": "Notification not found"},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=["patch"])
    def read_all(self, request):
        """
        Mark all notifications as read.
        
        PATCH /api/v1/notifications/read-all/
        
        Returns:
            {"success": true, "count": 10, "message": "10 notifications marked as read"}
        """
        count = NotificationService.mark_all_as_read(request.user)
        return Response({
            "success": True,
            "count": count,
            "message": f"{count} notification{'s' if count != 1 else ''} marked as read"
        })

    @action(detail=False, methods=["post"])
    def send_test(self, request):
        """
        Send a test notification to the authenticated user.
        
        POST /api/v1/notifications/send_test
        
        Optional body:
            {
                "title": "Custom Title",
                "message": "Custom Message",
                "send_push": true
            }
        
        Returns:
            {
                "success": true,
                "notification_id": "uuid",
                "message": "Test notification sent successfully"
            }
        """
        # Get custom title and message from request, or use defaults
        title = request.data.get("title", "Test Notification 🧪")
        message = request.data.get("message", "This is a test notification from Discount Buddy. If you're seeing this, notifications are working!")
        send_push = request.data.get("send_push", True)
        
        # Create the test notification
        notification = NotificationService.create_notification(
            user=request.user,
            title=title,
            message=message,
            notification_type="SYSTEM",
            send_push=send_push,
            payload={
                "test": True,
                "timestamp": str(Notification.objects.model._meta.get_field('created_at').auto_now_add)
            }
        )
        
        return Response({
            "success": True,
            "notification_id": str(notification.id),
            "message": "Test notification sent successfully",
            "push_sent": send_push,
            "device_count": DeviceToken.objects.filter(user=request.user, is_active=True).count()
        }, status=status.HTTP_201_CREATED)



class DeviceTokenViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing device tokens for push notifications.
    
    Endpoints:
    - GET /api/v1/notifications/devices/ - List user's device tokens
    - POST /api/v1/notifications/devices/ - Register a new device token
    - DELETE /api/v1/notifications/devices/{id}/ - Remove a device token
    """
    serializer_class = DeviceTokenSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return device tokens for the authenticated user only"""
        return DeviceToken.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        token = serializer.validated_data.get('token')
        device_type = serializer.validated_data.get('device_type')
        
        # Check if token already exists (even for a different user)
        # We want to re-assign it to the current user and ensure it's active
        existing_token = DeviceToken.objects.filter(token=token).first()
        
        if existing_token:
            existing_token.user = self.request.user
            existing_token.device_type = device_type
            existing_token.is_active = True
            existing_token.save()
            # We don't call super().perform_create() because we just manually updated
            # Set the serializer instance to the existing token so the response is correct
            serializer.instance = existing_token
        else:
            serializer.save(user=self.request.user)

    @action(detail=True, methods=["patch"])
    def deactivate(self, request, pk=None):
        """
        Deactivate a device token (soft delete).
        
        PATCH /api/v1/notifications/devices/{id}/deactivate/
        
        Returns:
            {"success": true, "message": "Device token deactivated"}
        """
        try:
            device_token = self.get_queryset().get(pk=pk)
            device_token.is_active = False
            device_token.save(update_fields=["is_active", "updated_at"])
            
            return Response({
                "success": True,
                "message": "Device token deactivated"
            })
        except DeviceToken.DoesNotExist:
            return Response(
                {"success": False, "message": "Device token not found"},
                status=status.HTTP_404_NOT_FOUND
            )
