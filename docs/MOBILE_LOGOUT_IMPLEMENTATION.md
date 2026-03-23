# Mobile App Authentication & Logout Guide

This document outlines how to properly manage access and refresh tokens, handle automatic token refreshing, and implement a secure logout process in the Discount Buddy mobile app.

---

## 1. Token Management Strategy

To ensure a seamless user experience where users stay logged in for up to 7 days without interruption, follow these steps.

### A. Secure Token Storage
**Never store tokens in plain text.** 
- **Flutter:** Use `flutter_secure_storage`.
- **iOS:** Use Keychain.
- **Android:** Use Encrypted Shared Preferences.

### B. The Interceptor Pattern
Use an **Interceptor** (like in `Dio` for Flutter) or a global HTTP wrapper to automate token injection and refreshing.

#### 1. Attach the Access Token
Add the `Authorization: Bearer <access_token>` header to every authenticated API request automatically.

#### 2. Handle 401 Unauthorized (Access Token Expiry)
The backend access tokens expire every **30 minutes**. When a request fails with a 401 error:
1.  **Pause** all other outgoing authenticated requests.
2.  **Call Refresh Endpoint**: POST the stored `refresh` token to `/users/token/refresh`.
    ```json
    { "refresh": "<your_stored_refresh_token>" }
    ```
3.  **Update Storage**: If the refresh is successful, save the new `access` token.
4.  **Retry Original Request**: Re-send the failed request using the new token.
5.  **Resume Operations**: Release the other paused requests.

#### 3. Handle Refresh Failure (The 7-Day Limit)
If the refresh call itself fails with a 401 or 403, the **7-day refresh period** has ended.
- **Action:** Clear all stored tokens and navigate the user back to the **Login screen**.

#### 4. Background Token Check (Optional)
Check the token's expiration timestamp locally (encoded in the JWT payload). If it’s within 1 minute of expiring, trigger the refresh *proactively* before sending the next API request.

---

## 2. Logout Implementation

Proper logout requires cleaning up both the server-side session and the local app state.

### A. Backend Logout API
- **URL:** `/users/logout`
- **Method:** `POST`
- **Headers:** `Authorization: Bearer <access_token>`
- **Payload:**
    ```json
    { "refresh": "<refresh_token_to_blacklist>" }
    ```
*Note: This "blacklists" the refresh token so it can never be used again.*

### B. Mobile App Logic Flow

```dart
Future<void> performLogout() async {
  try {
    // 1. Get tokens from storage
    final accessToken = await secureStorage.read(key: 'access_token');
    final refreshToken = await secureStorage.read(key: 'refresh_token');
    
    // 2. Terminate server session (Blacklist token)
    await apiService.post(
      '/users/logout', 
      data: {'refresh': refreshToken},
      options: Options(headers: {'Authorization': 'Bearer $accessToken'})
    );
  } catch (e) {
    // If network fails, still proceed with local cleanup
    print('Server logout failed, cleaning up local state...');
  } finally {
    // 3. Wipe all secure storage
    await secureStorage.deleteAll();
    
    // 4. Reset App State / Auth Provider
    authStatus.setUnauthenticated();
    
    // 5. Navigate to Login (Clear navigation stack)
    router.go('/login');
  }
}
```

---

## 3. Summary for Developers

| Event | Logic Requirement |
| :--- | :--- |
| **Login** | Save `access` and `refresh` tokens securely. |
| **Every Request** | Append `Authorization: Bearer <access_token>`. |
| **401 Error** | Try to refresh. If successful, retry request. |
| **Refresh Fails** | Force logout and clear all local data. |
| **Logout Button** | Call `/users/logout`, then delete all local tokens and redirect. |

## Relevant Endpoints
- **Obtain Tokens:** `/users/login` or `/users/token`
- **Refresh Token:** `/users/token/refresh`
- **Logout:** `/users/logout`
