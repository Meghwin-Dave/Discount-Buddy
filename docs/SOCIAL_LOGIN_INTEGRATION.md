# Social Login Integration Guide

This guide documents the integration of social login (Google & Apple) for the **Discount Buddy** mobile application.

## Unified OAuth Endpoint

To simplify the mobile app integration, a single consolidated endpoint has been created for all social login providers.

- **Endpoint**: `/users/oauth`
- **Method**: `POST`
- **Content-Type**: `application/json`

### Request Body Format

```json
{
  "provider": "google" | "apple",
  "token": "IDENTITY_TOKEN_OR_ID_TOKEN"
}
```

> **Note**: For backward compatibility, the endpoint also accepts `id_token`, `credential`, and `identityToken` as field names instead of `token`.

---

## Flutter Side Implementation

### 1. Dependencies
Add the following to your `pubspec.yaml`:
```yaml
dependencies:
  sign_in_with_apple: ^6.1.1 # latest version
  google_sign_in: ^6.2.1 # latest version
```

### 2. Apple Sign-In (iOS Only)
1.  **Xcode Setup**: Enable **"Sign in with Apple"** under **"Signing & Capabilities"** for your Runner target.
2.  **Flutter Implementation**:
    ```dart
    final credential = await SignInWithApple.getAppleIDCredential(
      scopes: [
        AppleIDAuthorizationScopes.email,
        AppleIDAuthorizationScopes.fullName,
      ],
    );

    if (credential.identityToken != null) {
      // Send credential.identityToken to backend with provider: 'apple'
    }
    ```

### 3. Google Sign-In
1.  **Configure Credentials**: Ensure Google OAuth Client IDs for Android and iOS are correctly set in the backend environment.
2.  **Flutter Implementation**:
    ```dart
    final GoogleSignInAccount? googleUser = await GoogleSignIn().signIn();
    final GoogleSignInAuthentication? googleAuth = await googleUser?.authentication;

    if (googleAuth?.idToken != null) {
      // Send googleAuth.idToken to backend with provider: 'google'
    }
    ```

---

## Unified Response Format

Upon successful login or registration, the server returns:

```json
{
  "access": "ACCESS_JWT_TOKEN",
  "refresh": "REFRESH_JWT_TOKEN",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "user",
    "first_name": "First",
    "last_name": "Last"
  },
  "role": "customer",
  "is_merchant": false,
  "is_customer": true
}
```

## Troubleshooting
- **Apple Email**: Apple only sends user profile data (email/name) on the **first sign-in attempt**. Subsequent attempts will only provide the token. The backend now handles this by using the Apple `sub` ID as a fallback identifier.
- **Bundle ID**: Ensure the Bundle ID matches `com.ketan.discountbuddy` exactly for Apple verification to succeed.
