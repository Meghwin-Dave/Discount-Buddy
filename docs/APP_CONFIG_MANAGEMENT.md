# App Configuration & Version Management

This document describes the implementation of the App Configuration and Version Management system for Discount Buddy.

## Backend Implementation (Django)

The backend is implemented as a Django app named `configs`.

### Endpoints

#### 1. Check App Version
- **URL**: `/api/app/version/check/`
- **Method**: `POST`
- **Auth Required**: No (AllowAny)
- **Request Body**:
```json
{
  "platform": "android",  // or "ios"
  "version": "1.0.0"
}
```
- **Response**:
```json
{
  "is_update_available": true,
  "update_type": "optional",  // none, optional, force, critical
  "is_force_update": false,
  "is_critical_update": false,
  "is_optional_update": true,
  "update_message": "A new version of DiscountBuddy is available!",
  "latest_version": "1.1.0",
  "minimum_version": "1.0.0",
  "store_url": "https://play.google.com/store/apps/details?id=com.discountbuddy"
}
```

#### 2. Manage Configs (Admin)
- **Base URL**: `/api/app/configs/`
- **Actions**: Standard CRUD (GET, POST, PUT, DELETE)
- **Auth Required**: Admin

### Evaluation Logic
The `AppConfigService` in `configs/services.py` evaluates the version based on thresholds stored in the `app_configs` table:
- `critical`: version < `MobileApp.CriticalVersion.{Platform}`
- `force`: version < `MobileApp.ForceUpdateThreshold.{Platform}`
- `optional`: version < `MobileApp.LatestVersion.{Platform}`

## Mobile Implementation (Flutter)

The mobile implementation resides in the `DiscountBuddy` directory.

### Components
1. **Model**: `lib/models/app_version_info.dart`
2. **Service**: `lib/services/app_config_service.dart`
3. **Widget**: `lib/widgets/update_dialog.dart`
4. **Integration**: Integrated in `SplashScreen` (`lib/pages/splash_screen.dart`).

### Workflow
On app launch (`SplashScreen`):
1. The app retrieves its current version and platform.
2. It calls the `/api/app/version/check/` API.
3. If an update is required (`force` or `critical`), an undismissable dialog is shown.
4. If an update is optional, a dismissible dialog is shown.
5. If no update, the app proceeds to the home/onboarding screen.
