# Mobile App - Push Notification Implementation Guide

## 🎯 Overview

This guide shows you how to integrate push notifications in your **Discount Buddy** mobile app (Android) using Firebase Cloud Messaging (FCM).

> **📚 API Reference:** For complete API endpoint documentation with request/response examples, see **[NOTIFICATION_API_REFERENCE.md](./NOTIFICATION_API_REFERENCE.md)**

## 📱 Your Firebase Project Details

- **Project ID:** `discount-buddy-d51bf`
- **Project Number:** `690749586825`
- **Package Name:** `com.discountbuddy.app`
- **App ID:** `1:690749586825:android:0b5963fa9d801a1c603558`
- **API Key:** `AIzaSyA7I_MnQ2HhMSEhKDpo2IcB3LzJAOSLnNA`
- **Storage Bucket:** `discount-buddy-d51bf.firebasestorage.app`

## 🚀 Backend Setup (✅ COMPLETE)

The backend is **fully configured** and ready:
- ✅ Firebase Admin SDK initialized
- ✅ Push notification service running
- ✅ API endpoints ready
- ✅ Automatic triggers configured

## 📲 Mobile App Integration

### Step 1: Add Firebase to Your Android App

#### 1.1 Download google-services.json

You already have the configuration. Create a file `google-services.json` in your Android app:

```json
{
  "project_info": {
    "project_number": "690749586825",
    "project_id": "discount-buddy-d51bf",
    "storage_bucket": "discount-buddy-d51bf.firebasestorage.app"
  },
  "client": [
    {
      "client_info": {
        "mobilesdk_app_id": "1:690749586825:android:0b5963fa9d801a1c603558",
        "android_client_info": {
          "package_name": "com.discountbuddy.app"
        }
      },
      "oauth_client": [],
      "api_key": [
        {
          "current_key": "AIzaSyA7I_MnQ2HhMSEhKDpo2IcB3LzJAOSLnNA"
        }
      ],
      "services": {
        "appinvite_service": {
          "other_platform_oauth_client": []
        }
      }
    }
  ],
  "configuration_version": "1"
}
```

**Location:** Place this file in `android/app/google-services.json`

#### 1.2 Update build.gradle Files

**Project-level build.gradle** (`android/build.gradle`):
```gradle
buildscript {
    dependencies {
        // Add this line
        classpath 'com.google.gms:google-services:4.4.0'
    }
}
```

**App-level build.gradle** (`android/app/build.gradle`):
```gradle
plugins {
    id 'com.android.application'
    // Add this line
    id 'com.google.gms.google-services'
}

dependencies {
    // Firebase Cloud Messaging
    implementation platform('com.google.firebase:firebase-bom:32.7.0')
    implementation 'com.google.firebase:firebase-messaging'
    implementation 'com.google.firebase:firebase-analytics'
}
```

### Step 2: Implement FCM in Your App

#### 2.1 Create FCM Service (Java/Kotlin)

**For Kotlin** (`MyFirebaseMessagingService.kt`):
```kotlin
package com.discountbuddy.app

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

class MyFirebaseMessagingService : FirebaseMessagingService() {

    override fun onNewToken(token: String) {
        super.onNewToken(token)
        
        // Send token to your backend
        sendTokenToServer(token)
    }

    override fun onMessageReceived(message: RemoteMessage) {
        super.onMessageReceived(message)
        
        // Handle notification
        message.notification?.let {
            showNotification(it.title ?: "", it.body ?: "", message.data)
        }
    }

    private fun sendTokenToServer(token: String) {
        // Get JWT token from your auth system
        val jwtToken = getStoredJwtToken() ?: return
        
        // Call your API to register device token
        val apiUrl = "http://your-api-url/user/api/notifications/devices/"
        
        // Use your HTTP client (Retrofit, OkHttp, etc.)
        // Example with Retrofit:
        /*
        val call = apiService.registerDeviceToken(
            token = "Bearer $jwtToken",
            body = DeviceTokenRequest(
                token = token,
                device_type = "android"
            )
        )
        call.enqueue(object : Callback<DeviceTokenResponse> {
            override fun onResponse(call: Call<DeviceTokenResponse>, response: Response<DeviceTokenResponse>) {
                if (response.isSuccessful) {
                    Log.d("FCM", "Token registered successfully")
                }
            }
            override fun onFailure(call: Call<DeviceTokenResponse>, t: Throwable) {
                Log.e("FCM", "Failed to register token", t)
            }
        })
        */
    }

    private fun showNotification(title: String, body: String, data: Map<String, String>) {
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channelId = "discount_buddy_notifications"
        
        // Create notification channel (Android 8.0+)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId,
                "Discount Buddy Notifications",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Notifications for deals, bookings, and updates"
            }
            notificationManager.createNotificationChannel(channel)
        }
        
        // Create intent for notification tap
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            
            // Add data to intent for deep linking
            data.forEach { (key, value) ->
                putExtra(key, value)
            }
        }
        
        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )
        
        // Build notification
        val notification = NotificationCompat.Builder(this, channelId)
            .setContentTitle(title)
            .setContentText(body)
            .setSmallIcon(R.drawable.ic_notification) // Add your icon
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .build()
        
        notificationManager.notify(System.currentTimeMillis().toInt(), notification)
    }
    
    private fun getStoredJwtToken(): String? {
        // Get JWT token from SharedPreferences or your auth system
        val prefs = getSharedPreferences("auth", Context.MODE_PRIVATE)
        return prefs.getString("jwt_token", null)
    }
}
```

**For Java** (`MyFirebaseMessagingService.java`):
```java
package com.discountbuddy.app;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import androidx.core.app.NotificationCompat;
import com.google.firebase.messaging.FirebaseMessagingService;
import com.google.firebase.messaging.RemoteMessage;
import java.util.Map;

public class MyFirebaseMessagingService extends FirebaseMessagingService {

    @Override
    public void onNewToken(String token) {
        super.onNewToken(token);
        sendTokenToServer(token);
    }

    @Override
    public void onMessageReceived(RemoteMessage message) {
        super.onMessageReceived(message);
        
        if (message.getNotification() != null) {
            String title = message.getNotification().getTitle();
            String body = message.getNotification().getBody();
            showNotification(title, body, message.getData());
        }
    }

    private void sendTokenToServer(String token) {
        // Implement API call to register token
        // See Kotlin example above
    }

    private void showNotification(String title, String body, Map<String, String> data) {
        NotificationManager notificationManager = 
            (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        String channelId = "discount_buddy_notifications";
        
        // Create notification channel (Android 8.0+)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                channelId,
                "Discount Buddy Notifications",
                NotificationManager.IMPORTANCE_HIGH
            );
            channel.setDescription("Notifications for deals, bookings, and updates");
            notificationManager.createNotificationChannel(channel);
        }
        
        // Create intent
        Intent intent = new Intent(this, MainActivity.class);
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
        
        // Add data for deep linking
        for (Map.Entry<String, String> entry : data.entrySet()) {
            intent.putExtra(entry.getKey(), entry.getValue());
        }
        
        PendingIntent pendingIntent = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT
        );
        
        // Build notification
        NotificationCompat.Builder builder = new NotificationCompat.Builder(this, channelId)
            .setContentTitle(title)
            .setContentText(body)
            .setSmallIcon(R.drawable.ic_notification)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .setPriority(NotificationCompat.PRIORITY_HIGH);
        
        notificationManager.notify((int) System.currentTimeMillis(), builder.build());
    }
}
```

#### 2.2 Register Service in AndroidManifest.xml

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.discountbuddy.app">

    <!-- Add permissions -->
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />

    <application
        android:name=".MyApplication"
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:theme="@style/AppTheme">

        <!-- Add FCM Service -->
        <service
            android:name=".MyFirebaseMessagingService"
            android:exported="false">
            <intent-filter>
                <action android:name="com.google.firebase.MESSAGING_EVENT" />
            </intent-filter>
        </service>

        <!-- Your activities -->
        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
```

### Step 3: Register Device Token with Backend

#### 3.1 Get FCM Token

**In your MainActivity or Application class:**

```kotlin
import com.google.firebase.messaging.FirebaseMessaging

class MainActivity : AppCompatActivity() {
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        
        // Get FCM token
        FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
            if (task.isSuccessful) {
                val token = task.result
                registerDeviceToken(token)
            }
        }
    }
    
    private fun registerDeviceToken(fcmToken: String) {
        // Get JWT token from your auth system
        val jwtToken = getJwtToken() ?: return
        
        // Call API to register device token
        val apiUrl = "http://192.168.29.221:8000/user/api/notifications/devices/"
        
        // Example with Retrofit
        val call = apiService.registerDeviceToken(
            authorization = "Bearer $jwtToken",
            body = DeviceTokenRequest(
                token = fcmToken,
                device_type = "android"
            )
        )
        
        call.enqueue(object : Callback<DeviceTokenResponse> {
            override fun onResponse(call: Call<DeviceTokenResponse>, response: Response<DeviceTokenResponse>) {
                if (response.isSuccessful) {
                    Log.d("FCM", "Device token registered successfully")
                } else {
                    Log.e("FCM", "Failed to register token: ${response.code()}")
                }
            }
            
            override fun onFailure(call: Call<DeviceTokenResponse>, t: Throwable) {
                Log.e("FCM", "Network error registering token", t)
            }
        })
    }
}
```

#### 3.2 API Models (Retrofit)

```kotlin
// API Service Interface
interface NotificationApiService {
    @POST("user/api/notifications/devices/")
    fun registerDeviceToken(
        @Header("Authorization") authorization: String,
        @Body body: DeviceTokenRequest
    ): Call<DeviceTokenResponse>
    
    @GET("user/api/notifications/")
    fun getNotifications(
        @Header("Authorization") authorization: String,
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20
    ): Call<NotificationListResponse>
    
    @GET("user/api/notifications/unread-count/")
    fun getUnreadCount(
        @Header("Authorization") authorization: String
    ): Call<UnreadCountResponse>
    
    @PATCH("user/api/notifications/{id}/mark-read/")
    fun markAsRead(
        @Header("Authorization") authorization: String,
        @Path("id") notificationId: String
    ): Call<MarkReadResponse>
}

// Request/Response Models
data class DeviceTokenRequest(
    val token: String,
    val device_type: String
)

data class DeviceTokenResponse(
    val id: String,
    val token: String,
    val device_type: String,
    val is_active: Boolean,
    val created_at: String
)

data class Notification(
    val id: String,
    val title: String,
    val message: String,
    val notification_type: String,
    val is_read: Boolean,
    val payload: Map<String, Any>?,
    val created_at: String
)

data class NotificationListResponse(
    val count: Int,
    val next: String?,
    val previous: String?,
    val results: List<Notification>
)

data class UnreadCountResponse(
    val count: Int
)

data class MarkReadResponse(
    val success: Boolean,
    val message: String
)
```

### Step 4: Handle Notification Taps (Deep Linking)

```kotlin
class MainActivity : AppCompatActivity() {
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        
        // Handle notification tap
        handleNotificationIntent(intent)
    }
    
    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        handleNotificationIntent(intent)
    }
    
    private fun handleNotificationIntent(intent: Intent?) {
        intent?.extras?.let { extras ->
            // Get notification data
            val bookingId = extras.getString("booking_id")
            val restaurantId = extras.getString("restaurant_id")
            val dealId = extras.getString("deal_id")
            
            // Navigate based on notification type
            when {
                bookingId != null -> {
                    // Navigate to booking details
                    navigateToBookingDetails(bookingId)
                }
                dealId != null -> {
                    // Navigate to deal details
                    navigateToDealDetails(dealId, restaurantId)
                }
                restaurantId != null -> {
                    // Navigate to restaurant details
                    navigateToRestaurantDetails(restaurantId)
                }
            }
        }
    }
    
    private fun navigateToBookingDetails(bookingId: String) {
        // Implement navigation to booking screen
        val intent = Intent(this, BookingDetailsActivity::class.java)
        intent.putExtra("booking_id", bookingId)
        startActivity(intent)
    }
    
    private fun navigateToDealDetails(dealId: String, restaurantId: String?) {
        // Implement navigation to deal screen
        val intent = Intent(this, DealDetailsActivity::class.java)
        intent.putExtra("deal_id", dealId)
        restaurantId?.let { intent.putExtra("restaurant_id", it) }
        startActivity(intent)
    }
    
    private fun navigateToRestaurantDetails(restaurantId: String) {
        // Implement navigation to restaurant screen
        val intent = Intent(this, RestaurantDetailsActivity::class.java)
        intent.putExtra("restaurant_id", restaurantId)
        startActivity(intent)
    }
}
```

### Step 5: Display In-App Notifications

Create a notifications screen to show in-app notifications:

```kotlin
class NotificationsActivity : AppCompatActivity() {
    
    private lateinit var recyclerView: RecyclerView
    private lateinit var adapter: NotificationAdapter
    private val notifications = mutableListOf<Notification>()
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_notifications)
        
        setupRecyclerView()
        loadNotifications()
    }
    
    private fun setupRecyclerView() {
        recyclerView = findViewById(R.id.notificationsRecyclerView)
        adapter = NotificationAdapter(notifications) { notification ->
            onNotificationClicked(notification)
        }
        recyclerView.adapter = adapter
        recyclerView.layoutManager = LinearLayoutManager(this)
    }
    
    private fun loadNotifications() {
        val jwtToken = getJwtToken() ?: return
        
        apiService.getNotifications("Bearer $jwtToken").enqueue(object : Callback<NotificationListResponse> {
            override fun onResponse(call: Call<NotificationListResponse>, response: Response<NotificationListResponse>) {
                if (response.isSuccessful) {
                    response.body()?.let { data ->
                        notifications.clear()
                        notifications.addAll(data.results)
                        adapter.notifyDataSetChanged()
                    }
                }
            }
            
            override fun onFailure(call: Call<NotificationListResponse>, t: Throwable) {
                Log.e("Notifications", "Failed to load notifications", t)
            }
        })
    }
    
    private fun onNotificationClicked(notification: Notification) {
        // Mark as read
        markAsRead(notification.id)
        
        // Navigate based on payload
        notification.payload?.let { payload ->
            val bookingId = payload["booking_id"] as? String
            val dealId = payload["deal_id"] as? String
            val restaurantId = payload["restaurant_id"] as? String
            
            when {
                bookingId != null -> navigateToBookingDetails(bookingId)
                dealId != null -> navigateToDealDetails(dealId, restaurantId)
                restaurantId != null -> navigateToRestaurantDetails(restaurantId)
            }
        }
    }
    
    private fun markAsRead(notificationId: String) {
        val jwtToken = getJwtToken() ?: return
        
        apiService.markAsRead("Bearer $jwtToken", notificationId).enqueue(object : Callback<MarkReadResponse> {
            override fun onResponse(call: Call<MarkReadResponse>, response: Response<MarkReadResponse>) {
                if (response.isSuccessful) {
                    // Update UI
                    val index = notifications.indexOfFirst { it.id == notificationId }
                    if (index != -1) {
                        notifications[index] = notifications[index].copy(is_read = true)
                        adapter.notifyItemChanged(index)
                    }
                }
            }
            
            override fun onFailure(call: Call<MarkReadResponse>, t: Throwable) {
                Log.e("Notifications", "Failed to mark as read", t)
            }
        })
    }
}
```

### Step 6: Show Unread Badge

```kotlin
class HomeActivity : AppCompatActivity() {
    
    private lateinit var notificationBadge: TextView
    
    override fun onResume() {
        super.onResume()
        updateNotificationBadge()
    }
    
    private fun updateNotificationBadge() {
        val jwtToken = getJwtToken() ?: return
        
        apiService.getUnreadCount("Bearer $jwtToken").enqueue(object : Callback<UnreadCountResponse> {
            override fun onResponse(call: Call<UnreadCountResponse>, response: Response<UnreadCountResponse>) {
                if (response.isSuccessful) {
                    response.body()?.let { data ->
                        if (data.count > 0) {
                            notificationBadge.visibility = View.VISIBLE
                            notificationBadge.text = if (data.count > 99) "99+" else data.count.toString()
                        } else {
                            notificationBadge.visibility = View.GONE
                        }
                    }
                }
            }
            
            override fun onFailure(call: Call<UnreadCountResponse>, t: Throwable) {
                Log.e("Badge", "Failed to get unread count", t)
            }
        })
    }
}
```

## 📊 Notification Types & Payloads

### 1. Booking Confirmed

**Push Notification:**
```json
{
  "notification": {
    "title": "Booking Confirmed 🎉",
    "body": "Your table at Pizza Palace has been confirmed for March 15, 2026 at 07:30 PM."
  },
  "data": {
    "booking_id": "uuid-here",
    "restaurant_id": "uuid-here",
    "booking_date": "2026-03-15T19:30:00Z"
  }
}
```

**Action:** Navigate to booking details screen

### 2. Favorite Restaurant Deal

**Push Notification:**
```json
{
  "notification": {
    "title": "New Deal Available 🔥",
    "body": "Pizza Palace has launched a new offer: 50% off all pizzas. Check it out!"
  },
  "data": {
    "restaurant_id": "uuid-here",
    "deal_id": "uuid-here"
  }
}
```

**Action:** Navigate to deal details or restaurant screen

### 3. Deal Redeemed

**Push Notification:**
```json
{
  "notification": {
    "title": "Deal Redeemed Successfully ✅",
    "body": "Enjoy your offer at Pizza Palace. Bon appétit!"
  },
  "data": {
    "deal_id": "uuid-here",
    "restaurant_id": "uuid-here"
  }
}
```

**Action:** Navigate to deal history or restaurant screen

## 🧪 Testing

### Test 1: Register Device Token

1. Run your app
2. Login with a user account
3. Check backend logs to see token registration
4. Verify in Django admin: `/admin/notifications/devicetoken/`

### Test 2: Send Test Notification

Use Django shell:
```python
from users.models import User
from notifications.services import NotificationService

user = User.objects.get(email='your@email.com')

NotificationService.create_notification(
    user=user,
    title="Test Push 🚀",
    message="If you see this, push notifications are working!",
    notification_type="SYSTEM",
    send_push=True
)
```

### Test 3: Trigger Automatic Notifications

**Test Booking Confirmation:**
```python
from restaurants.models import Booking

booking = Booking.objects.filter(user=user).first()
booking.status = 'confirmed'
booking.save()
# Should send push notification
```

## 🔧 Troubleshooting

### Issue: Not Receiving Push Notifications

**Solutions:**
1. Check device token is registered in backend
2. Verify Firebase credentials are correct
3. Check Celery worker is running
4. Check app has notification permissions
5. Test with Firebase Console (Cloud Messaging → Send test message)

### Issue: Token Not Registering

**Solutions:**
1. Check API URL is correct
2. Verify JWT token is valid
3. Check network connectivity
4. Review API error response

### Issue: Notification Not Showing

**Solutions:**
1. Check notification channel is created (Android 8.0+)
2. Verify notification permission granted
3. Check notification icon exists
4. Review device notification settings

## 📱 Best Practices

1. **Request Permission:** Ask for notification permission at appropriate time
2. **Handle Token Refresh:** Register new token when `onNewToken` is called
3. **Sync on Login:** Register device token every time user logs in
4. **Unregister on Logout:** Deactivate token when user logs out
5. **Handle Background/Foreground:** Show notifications differently based on app state
6. **Deep Linking:** Always handle notification taps with proper navigation
7. **Badge Updates:** Update unread count when app comes to foreground
8. **Error Handling:** Handle network errors gracefully

## 🎉 Summary

Your push notification system is now **fully configured**:

- ✅ Backend: Firebase Admin SDK initialized
- ✅ Backend: API endpoints ready
- ✅ Backend: Automatic triggers working
- ✅ Mobile: Integration guide complete
- ✅ Mobile: Code examples provided
- ✅ Testing: Instructions included

**Next Steps:**
1. Integrate FCM in your Android app
2. Test device token registration
3. Test push notifications
4. Implement in-app notification screen
5. Add deep linking for notification taps

---

**Need Help?** Check the backend documentation in `NOTIFICATION_SYSTEM_README.md` or test the API endpoints using the examples in `NOTIFICATION_QUICK_START.md`.
