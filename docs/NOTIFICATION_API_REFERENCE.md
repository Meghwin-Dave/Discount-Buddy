# Discount Buddy - Notification API Reference for Mobile

## 📡 Base URLs

- **Development:** `http://192.168.29.221:8000`
- **User API Base:** `/user/api/notifications/`
- **Merchant API Base:** `/merchant/api/notifications/`

## 🔐 Authentication

All endpoints require JWT authentication. Include the token in the Authorization header:

```
Authorization: Bearer YOUR_JWT_TOKEN
```

Get JWT token from login endpoint:
```bash
POST /user/api/users/login/
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}

Response:
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": { ... }
}
```

---

## 📱 Device Token Endpoints

### 1. Register Device Token

Register or update an FCM device token for push notifications.

**Endpoint:** `POST /user/api/notifications/devices`

**Headers:**
```
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json
```

**Request Body:**
```json
{
  "token": "fGcM_dEvIcE_tOkEn_HeRe_VeRy_LoNg_StRiNg",
  "device_type": "android"
}
```

**Parameters:**
- `token` (string, required): FCM device token
- `device_type` (string, required): Device type - `"android"`, `"ios"`, or `"web"`

**Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "token": "fGcM_dEvIcE_tOkEn_HeRe_VeRy_LoNg_StRiNg",
  "device_type": "android",
  "is_active": true,
  "created_at": "2026-02-13T10:30:00Z"
}
```

**Android Example (Kotlin):**
```kotlin
// Get FCM token
FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
    if (task.isSuccessful) {
        val fcmToken = task.result
        registerDeviceToken(fcmToken)
    }
}

fun registerDeviceToken(fcmToken: String) {
    val request = DeviceTokenRequest(
        token = fcmToken,
        device_type = "android"
    )
    
    apiService.registerDeviceToken(
        authorization = "Bearer $jwtToken",
        body = request
    ).enqueue(object : Callback<DeviceTokenResponse> {
        override fun onResponse(call: Call<DeviceTokenResponse>, response: Response<DeviceTokenResponse>) {
            if (response.isSuccessful) {
                Log.d("FCM", "Token registered: ${response.body()?.id}")
            }
        }
        override fun onFailure(call: Call<DeviceTokenResponse>, t: Throwable) {
            Log.e("FCM", "Failed to register token", t)
        }
    })
}
```

**cURL Example:**
```bash
curl -X POST http://192.168.29.221:8000/user/api/notifications/devices \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "fGcM_dEvIcE_tOkEn_HeRe",
    "device_type": "android"
  }'
```

---

### 2. List Device Tokens

Get all device tokens for the authenticated user.

**Endpoint:** `GET /user/api/notifications/devices`

**Headers:**
```
Authorization: Bearer YOUR_JWT_TOKEN
```

**Response (200 OK):**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "token": "fGcM_dEvIcE_tOkEn_1",
    "device_type": "android",
    "is_active": true,
    "created_at": "2026-02-13T10:30:00Z"
  },
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "token": "fGcM_dEvIcE_tOkEn_2",
    "device_type": "android",
    "is_active": true,
    "created_at": "2026-02-12T08:15:00Z"
  }
]
```

**Android Example (Kotlin):**
```kotlin
apiService.getDeviceTokens("Bearer $jwtToken")
    .enqueue(object : Callback<List<DeviceTokenResponse>> {
        override fun onResponse(call: Call<List<DeviceTokenResponse>>, response: Response<List<DeviceTokenResponse>>) {
            if (response.isSuccessful) {
                val tokens = response.body()
                Log.d("FCM", "User has ${tokens?.size} registered devices")
            }
        }
        override fun onFailure(call: Call<List<DeviceTokenResponse>>, t: Throwable) {
            Log.e("FCM", "Failed to get tokens", t)
        }
    })
```

---

### 3. Deactivate Device Token

Deactivate a device token (e.g., when user logs out).

**Endpoint:** `PATCH /user/api/notifications/devices{id}/deactivate`

**Headers:**
```
Authorization: Bearer YOUR_JWT_TOKEN
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Device token deactivated"
}
```

**Android Example (Kotlin):**
```kotlin
fun deactivateToken(tokenId: String) {
    apiService.deactivateDeviceToken(
        authorization = "Bearer $jwtToken",
        tokenId = tokenId
    ).enqueue(object : Callback<SuccessResponse> {
        override fun onResponse(call: Call<SuccessResponse>, response: Response<SuccessResponse>) {
            if (response.isSuccessful) {
                Log.d("FCM", "Token deactivated")
            }
        }
        override fun onFailure(call: Call<SuccessResponse>, t: Throwable) {
            Log.e("FCM", "Failed to deactivate", t)
        }
    })
}

// Call this on logout
fun onUserLogout() {
    val tokenId = getStoredTokenId()
    if (tokenId != null) {
        deactivateToken(tokenId)
    }
}
```

---

### 4. Delete Device Token

Permanently delete a device token.

**Endpoint:** `DELETE /user/api/notifications/devices{id}/`

**Headers:**
```
Authorization: Bearer YOUR_JWT_TOKEN
```

**Response (204 No Content)**

**Android Example (Kotlin):**
```kotlin
apiService.deleteDeviceToken(
    authorization = "Bearer $jwtToken",
    tokenId = tokenId
).enqueue(object : Callback<Void> {
    override fun onResponse(call: Call<Void>, response: Response<Void>) {
        if (response.isSuccessful) {
            Log.d("FCM", "Token deleted")
        }
    }
    override fun onFailure(call: Call<Void>, t: Throwable) {
        Log.e("FCM", "Failed to delete", t)
    }
})
```

---

## 🔔 Notification Endpoints

### 5. List Notifications

Get paginated list of notifications for the authenticated user.

**Endpoint:** `GET /user/api/notifications/`

**Headers:**
```
Authorization: Bearer YOUR_JWT_TOKEN
```

**Query Parameters:**
- `page` (integer, optional): Page number (default: 1)
- `page_size` (integer, optional): Items per page (default: 20, max: 100)

**Response (200 OK):**
```json
{
  "count": 45,
  "next": "http://192.168.29.221:8000/user/api/notifications/?page=2",
  "previous": null,
  "results": [
    {
      "id": "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d",
      "title": "Booking Confirmed 🎉",
      "message": "Your table at Pizza Palace has been confirmed for March 15, 2026 at 07:30 PM.",
      "notification_type": "BOOKING_CONFIRMED",
      "is_read": false,
      "payload": {
        "booking_id": "b1c2d3e4-f5a6-4b5c-8d9e-0f1a2b3c4d5e",
        "restaurant_id": "c1d2e3f4-a5b6-4c5d-8e9f-0a1b2c3d4e5f",
        "booking_date": "2026-03-15T19:30:00Z"
      },
      "source_id": "b1c2d3e4-f5a6-4b5c-8d9e-0f1a2b3c4d5e",
      "source_type": "booking",
      "created_at": "2026-02-13T10:30:00Z"
    },
    {
      "id": "d1e2f3a4-b5c6-4d5e-8f9a-0b1c2d3e4f5a",
      "title": "New Deal Available 🔥",
      "message": "Pizza Palace has launched a new offer: 50% off all pizzas. Check it out!",
      "notification_type": "FAV_DEAL",
      "is_read": true,
      "payload": {
        "restaurant_id": "c1d2e3f4-a5b6-4c5d-8e9f-0a1b2c3d4e5f",
        "deal_id": "e1f2a3b4-c5d6-4e5f-8a9b-0c1d2e3f4a5b"
      },
      "source_id": "e1f2a3b4-c5d6-4e5f-8a9b-0c1d2e3f4a5b",
      "source_type": "deal",
      "created_at": "2026-02-12T14:20:00Z"
    }
  ]
}
```

**Android Example (Kotlin):**
```kotlin
fun loadNotifications(page: Int = 1) {
    apiService.getNotifications(
        authorization = "Bearer $jwtToken",
        page = page,
        pageSize = 20
    ).enqueue(object : Callback<NotificationListResponse> {
        override fun onResponse(call: Call<NotificationListResponse>, response: Response<NotificationListResponse>) {
            if (response.isSuccessful) {
                response.body()?.let { data ->
                    val notifications = data.results
                    val totalCount = data.count
                    val hasMore = data.next != null
                    
                    // Update UI
                    adapter.submitList(notifications)
                }
            }
        }
        override fun onFailure(call: Call<NotificationListResponse>, t: Throwable) {
            Log.e("Notifications", "Failed to load", t)
        }
    })
}
```

**cURL Example:**
```bash
curl -X GET "http://192.168.29.221:8000/user/api/notifications/?page=1&page_size=20" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### 6. Get Single Notification

Get details of a specific notification.

**Endpoint:** `GET /user/api/notifications/{id}/`

**Headers:**
```
Authorization: Bearer YOUR_JWT_TOKEN
```

**Response (200 OK):**
```json
{
  "id": "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d",
  "title": "Booking Confirmed 🎉",
  "message": "Your table at Pizza Palace has been confirmed for March 15, 2026 at 07:30 PM.",
  "notification_type": "BOOKING_CONFIRMED",
  "is_read": false,
  "payload": {
    "booking_id": "b1c2d3e4-f5a6-4b5c-8d9e-0f1a2b3c4d5e",
    "restaurant_id": "c1d2e3f4-a5b6-4c5d-8e9f-0a1b2c3d4e5f",
    "booking_date": "2026-03-15T19:30:00Z"
  },
  "source_id": "b1c2d3e4-f5a6-4b5c-8d9e-0f1a2b3c4d5e",
  "source_type": "booking",
  "created_at": "2026-02-13T10:30:00Z"
}
```

---

### 7. Get Unread Count

Get the count of unread notifications (for badge display).

**Endpoint:** `GET /user/api/notifications/unread_count`

**Headers:**
```
Authorization: Bearer YOUR_JWT_TOKEN
```

**Response (200 OK):**
```json
{
  "count": 5
}
```

**Android Example (Kotlin):**
```kotlin
fun updateNotificationBadge() {
    apiService.getUnreadCount("Bearer $jwtToken")
        .enqueue(object : Callback<UnreadCountResponse> {
            override fun onResponse(call: Call<UnreadCountResponse>, response: Response<UnreadCountResponse>) {
                if (response.isSuccessful) {
                    val count = response.body()?.count ?: 0
                    
                    // Update badge
                    if (count > 0) {
                        badgeView.visibility = View.VISIBLE
                        badgeView.text = if (count > 99) "99+" else count.toString()
                    } else {
                        badgeView.visibility = View.GONE
                    }
                }
            }
            override fun onFailure(call: Call<UnreadCountResponse>, t: Throwable) {
                Log.e("Badge", "Failed to get count", t)
            }
        })
}

// Call this when app comes to foreground
override fun onResume() {
    super.onResume()
    updateNotificationBadge()
}
```

**cURL Example:**
```bash
curl -X GET http://192.168.29.221:8000/user/api/notifications/unread_count \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### 8. Mark Notification as Read

Mark a specific notification as read.

**Endpoint:** `PATCH /user/api/notifications/{id}/mark_read`

**Headers:**
```
Authorization: Bearer YOUR_JWT_TOKEN
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Notification marked as read"
}
```

**Android Example (Kotlin):**
```kotlin
fun markAsRead(notificationId: String) {
    apiService.markAsRead(
        authorization = "Bearer $jwtToken",
        notificationId = notificationId
    ).enqueue(object : Callback<MarkReadResponse> {
        override fun onResponse(call: Call<MarkReadResponse>, response: Response<MarkReadResponse>) {
            if (response.isSuccessful) {
                // Update UI
                updateNotificationInList(notificationId, isRead = true)
                updateNotificationBadge() // Refresh badge count
            }
        }
        override fun onFailure(call: Call<MarkReadResponse>, t: Throwable) {
            Log.e("Notifications", "Failed to mark as read", t)
        }
    })
}

// Call when user taps on notification
fun onNotificationClicked(notification: Notification) {
    if (!notification.is_read) {
        markAsRead(notification.id)
    }
    navigateToDetails(notification)
}
```

**cURL Example:**
```bash
curl -X PATCH http://192.168.29.221:8000/user/api/notifications/a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d/mark_read \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### 9. Mark All as Read

Mark all notifications as read for the authenticated user.

**Endpoint:** `PATCH /user/api/notifications/read_all`

**Headers:**
```
Authorization: Bearer YOUR_JWT_TOKEN
```

**Response (200 OK):**
```json
{
  "success": true,
  "count": 5,
  "message": "5 notifications marked as read"
}
```

**Android Example (Kotlin):**
```kotlin
fun markAllAsRead() {
    apiService.markAllAsRead("Bearer $jwtToken")
        .enqueue(object : Callback<MarkAllReadResponse> {
            override fun onResponse(call: Call<MarkAllReadResponse>, response: Response<MarkAllReadResponse>) {
                if (response.isSuccessful) {
                    val count = response.body()?.count ?: 0
                    Toast.makeText(this@NotificationsActivity, 
                        "$count notifications marked as read", 
                        Toast.LENGTH_SHORT).show()
                    
                    // Refresh list
                    loadNotifications()
                    updateNotificationBadge()
                }
            }
            override fun onFailure(call: Call<MarkAllReadResponse>, t: Throwable) {
                Log.e("Notifications", "Failed to mark all as read", t)
            }
        })
}

// Add "Mark all as read" button
markAllButton.setOnClickListener {
    markAllAsRead()
}
```

**cURL Example:**
```bash
curl -X PATCH http://192.168.29.221:8000/user/api/notifications/read_all \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## 📊 Notification Types & Payloads

### BOOKING_CONFIRMED

**When:** Booking status changes to CONFIRMED

**Payload:**
```json
{
  "booking_id": "uuid",
  "restaurant_id": "uuid",
  "booking_date": "2026-03-15T19:30:00Z"
}
```

**Action:** Navigate to booking details screen

---

### FAV_DEAL

**When:** New deal created at a favorited restaurant

**Payload:**
```json
{
  "restaurant_id": "uuid",
  "deal_id": "uuid"
}
```

**Action:** Navigate to deal details or restaurant screen

---

### DEAL_REDEEMED

**When:** User successfully redeems a deal

**Payload:**
```json
{
  "deal_id": "uuid",
  "restaurant_id": "uuid"
}
```

**Action:** Navigate to deal history or restaurant screen

---

### SYSTEM

**When:** Manual system announcements

**Payload:**
```json
{
  "action": "string",
  "custom_data": "any"
}
```

**Action:** Based on payload content

---

## 🔧 Complete Retrofit Interface

```kotlin
interface NotificationApiService {
    
    // Device Token Endpoints
    @POST("user/api/notifications/devices")
    fun registerDeviceToken(
        @Header("Authorization") authorization: String,
        @Body body: DeviceTokenRequest
    ): Call<DeviceTokenResponse>
    
    @GET("user/api/notifications/devices")
    fun getDeviceTokens(
        @Header("Authorization") authorization: String
    ): Call<List<DeviceTokenResponse>>
    
    @PATCH("user/api/notifications/devices/{id}/deactivate")
    fun deactivateDeviceToken(
        @Header("Authorization") authorization: String,
        @Path("id") tokenId: String
    ): Call<SuccessResponse>
    
    @DELETE("user/api/notifications/devices/{id}")
    fun deleteDeviceToken(
        @Header("Authorization") authorization: String,
        @Path("id") tokenId: String
    ): Call<Void>
    
    // Notification Endpoints
    @GET("user/api/notifications")
    fun getNotifications(
        @Header("Authorization") authorization: String,
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 20
    ): Call<NotificationListResponse>
    
    @GET("user/api/notifications/{id}")
    fun getNotification(
        @Header("Authorization") authorization: String,
        @Path("id") notificationId: String
    ): Call<Notification>
    
    @GET("user/api/notifications/unread_count")
    fun getUnreadCount(
        @Header("Authorization") authorization: String
    ): Call<UnreadCountResponse>
    
    @PATCH("user/api/notifications/{id}/mark_read")
    fun markAsRead(
        @Header("Authorization") authorization: String,
        @Path("id") notificationId: String
    ): Call<MarkReadResponse>
    
    @PATCH("user/api/notifications/read_all")
    fun markAllAsRead(
        @Header("Authorization") authorization: String
    ): Call<MarkAllReadResponse>
}
```

## 📦 Data Models

```kotlin
// Request Models
data class DeviceTokenRequest(
    val token: String,
    val device_type: String // "android", "ios", or "web"
)

// Response Models
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
    val source_id: String?,
    val source_type: String?,
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

data class MarkAllReadResponse(
    val success: Boolean,
    val count: Int,
    val message: String
)

data class SuccessResponse(
    val success: Boolean,
    val message: String
)
```

## 🚀 Complete Usage Flow

### 1. On App Launch / Login

```kotlin
fun onUserLogin(jwtToken: String) {
    // Save JWT token
    saveJwtToken(jwtToken)
    
    // Get FCM token and register
    FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
        if (task.isSuccessful) {
            val fcmToken = task.result
            registerDeviceToken(fcmToken)
        }
    }
    
    // Load notifications
    loadNotifications()
    
    // Update badge
    updateNotificationBadge()
}
```

### 2. On App Resume

```kotlin
override fun onResume() {
    super.onResume()
    
    // Refresh badge count
    updateNotificationBadge()
    
    // Optionally refresh notifications
    if (shouldRefreshNotifications()) {
        loadNotifications()
    }
}
```

### 3. On Logout

```kotlin
fun onUserLogout() {
    // Deactivate device token
    val tokenId = getStoredTokenId()
    if (tokenId != null) {
        deactivateDeviceToken(tokenId)
    }
    
    // Clear local data
    clearJwtToken()
    clearNotifications()
}
```

### 4. On Push Notification Received

```kotlin
override fun onMessageReceived(message: RemoteMessage) {
    // Show notification
    showNotification(message)
    
    // Update badge if app is in foreground
    if (isAppInForeground()) {
        updateNotificationBadge()
        refreshNotificationList()
    }
}
```

---

## 🎯 Best Practices

1. **Token Management**
   - Register token on every login
   - Refresh token when `onNewToken()` is called
   - Deactivate token on logout

2. **Badge Updates**
   - Update on app resume
   - Update after marking as read
   - Update when push notification received

3. **Error Handling**
   - Handle 401 (Unauthorized) - refresh JWT token
   - Handle 404 (Not Found) - notification may be deleted
   - Handle network errors gracefully

4. **Performance**
   - Use pagination for notification list
   - Cache notifications locally
   - Implement pull-to-refresh

5. **User Experience**
   - Show loading states
   - Provide feedback on actions
   - Handle deep linking properly

---

## 📞 Support

For issues or questions:
- Check backend logs for API errors
- Verify JWT token is valid
- Test endpoints with cURL first
- Review `NOTIFICATION_SYSTEM_README.md` for backend details
