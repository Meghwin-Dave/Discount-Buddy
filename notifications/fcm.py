"""
Firebase Cloud Messaging (FCM) helper functions.

This module handles sending push notifications via Firebase.

Setup Instructions:
1. Install firebase-admin: pip install firebase-admin
2. Download your Firebase service account JSON file from Firebase Console
3. Add to settings.py:
   - FIREBASE_CREDENTIALS_PATH = BASE_DIR / "path/to/serviceAccountKey.json"
   OR
   - Set environment variable FIREBASE_CREDENTIALS with JSON content
"""
import logging
from typing import Dict, Any, Optional

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Firebase Admin SDK will be initialized lazily
_firebase_app = None


def initialize_firebase():
    """
    Initialize Firebase Admin SDK.
    This is called lazily when first FCM message is sent.
    """
    global _firebase_app
    
    if _firebase_app is not None:
        return _firebase_app
    
    try:
        import firebase_admin
        from firebase_admin import credentials
        from django.conf import settings
        import os
        
        # Try to get credentials from settings or environment
        cred = None
        
        # Option 1: Path to service account JSON file
        if hasattr(settings, 'FIREBASE_CREDENTIALS_PATH'):
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        
        # Option 2: JSON content from environment variable
        elif os.environ.get('FIREBASE_CREDENTIALS'):
            import json
            cred_dict = json.loads(os.environ.get('FIREBASE_CREDENTIALS'))
            cred = credentials.Certificate(cred_dict)
        
        else:
            logger.warning(
                "Firebase credentials not configured. "
                "Set FIREBASE_CREDENTIALS_PATH in settings.py or "
                "FIREBASE_CREDENTIALS environment variable."
            )
            return None
        
        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully")
        print("✅ [FCM] Firebase Admin SDK initialized successfully with credentials")
        return _firebase_app
        
    except ImportError:
        logger.error(
            "firebase-admin package not installed. "
            "Install it with: pip install firebase-admin"
        )
        print("❌ [FCM] firebase-admin package NOT installed")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {str(e)}")
        print(f"❌ [FCM] Failed to initialize Firebase: {str(e)}")
        return None


def send_fcm_message(
    token: str,
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
    image_url: Optional[str] = None,
) -> bool:
    """
    Send a push notification via Firebase Cloud Messaging.
    
    Args:
        token: FCM device token
        title: Notification title
        body: Notification body/message
        data: Optional data payload (must be string key-value pairs)
        image_url: Optional image URL for rich notification
    
    Returns:
        True if sent successfully, False otherwise
    """
    try:
        # Initialize Firebase if not already done
        if initialize_firebase() is None:
            logger.warning("Firebase not initialized, skipping push notification")
            print("⚠️ [FCM] Firebase not initialized, skipping push notification")
            return False
        
        from firebase_admin import messaging
        
        # Convert data values to strings (FCM requirement)
        if data:
            data = {k: str(v) for k, v in data.items()}
        
        # Build notification
        notification = messaging.Notification(
            title=title,
            body=body,
            image=image_url,
        )
        
        # Build message
        message = messaging.Message(
            notification=notification,
            data=data,
            token=token,
        )
        
        # Send message
        print(f"🚀 [FCM] Attempting to send message to token prefix: {token[:10]}...")
        response = messaging.send(message)
        logger.info(f"Successfully sent FCM message: {response}")
        print(f"✅ [FCM] Successfully sent FCM message. Response ID: {response}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send FCM message: {str(e)}")
        print(f"❌ [FCM] Failed to send FCM message: {str(e)}")
        return False


def send_fcm_multicast(
    tokens: list,
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
    image_url: Optional[str] = None,
) -> Dict[str, int]:
    """
    Send push notification to multiple devices at once.
    More efficient than sending individual messages.
    
    Args:
        tokens: List of FCM device tokens
        title: Notification title
        body: Notification body/message
        data: Optional data payload
        image_url: Optional image URL
    
    Returns:
        Dictionary with success_count and failure_count
    """
    try:
        if initialize_firebase() is None:
            logger.warning("Firebase not initialized, skipping multicast")
            return {"success_count": 0, "failure_count": len(tokens)}
        
        from firebase_admin import messaging
        
        # Convert data values to strings
        if data:
            data = {k: str(v) for k, v in data.items()}
        
        # Build notification
        notification = messaging.Notification(
            title=title,
            body=body,
            image=image_url,
        )
        
        # Build multicast message
        message = messaging.MulticastMessage(
            notification=notification,
            data=data,
            tokens=tokens,
        )
        
        # Send multicast
        response = messaging.send_multicast(message)
        
        logger.info(
            f"Multicast sent: {response.success_count} success, "
            f"{response.failure_count} failures"
        )
        
        return {
            "success_count": response.success_count,
            "failure_count": response.failure_count,
        }
        
    except Exception as e:
        logger.error(f"Failed to send FCM multicast: {str(e)}")
        return {"success_count": 0, "failure_count": len(tokens)}
