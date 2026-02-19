# QR Code Redemption Implementation Guide

## Overview

This document describes how to implement QR code scanning functionality in the Flutter app to allow merchants to scan and redeem user deals. The system uses a QR code generated when users claim a deal, which merchants can scan to validate and redeem the deal.

---

## System Architecture

### Flow Diagram

```
User Side (Customer App):
1. User claims a deal → POST /api/deals/{id}/use/
2. Backend generates:
   - 6-digit redemption code (e.g., "123456")
   - QR code image containing: "DEALUSE:<deal_use_id>:<redemption_code>"
3. User receives DealUse object with QR code URL

Merchant Side (Restaurant App):
1. Merchant opens QR scanner
2. Scans user's QR code
3. Extracts QR data: "DEALUSE:105:123456"
4. Sends to backend → POST /merchant/api/deals/redeem
5. Backend validates and marks deal as redeemed
6. Returns success/error response
```

---

## QR Code Format

### QR Code Payload Structure

The QR code contains a string in the following format:

```
DEALUSE:<deal_use_id>:<redemption_code>
```

**Example:**
```
DEALUSE:105:123456
```

**Components:**
- `DEALUSE` - Fixed prefix to identify the QR type
- `<deal_use_id>` - Unique ID of the DealUse record (e.g., 105)
- `<redemption_code>` - 6-digit numeric code (e.g., 123456)

### Why This Format?

- **Validation**: The prefix ensures we're scanning the correct type of QR code
- **Security**: Both ID and code must match for redemption
- **Fallback**: Merchants can manually enter the 6-digit code if scanning fails

---

## API Endpoints

### 1. User Claims Deal (Customer App)

**Endpoint:** `POST /api/deals/{deal_id}/use/`

**Authentication:** Required (User token)

**Request Body:**
```json
{
  "notes": "Optional notes about the deal usage"
}
```

**Response (201 Created):**
```json
{
  "id": 105,
  "deal": {
    "id": 42,
    "title": "50% Off Main Course",
    "description": "Get 50% discount on any main course",
    "deal_type": "percentage",
    "discount_percentage": 50.0,
    "discount_amount": null,
    "restaurant_name": "The Italian Place",
    "restaurant_slug": "the-italian-place",
    "city_name": "Mumbai",
    "start_date": "2026-02-01T00:00:00Z",
    "end_date": "2026-03-31T23:59:59Z",
    "is_featured": true,
    "primary_image": "https://api.example.com/media/deals/deal_42.jpg",
    "is_active": true
  },
  "used_at": "2026-02-17T09:54:44Z",
  "restaurant_confirmed": false,
  "notes": "",
  "redemption_code": "123456",
  "qr_code": "/media/qr_codes/qr_105.png",
  "qr_code_url": "https://api.example.com/media/qr_codes/qr_105.png",
  "is_redeemed": false,
  "redeemed_at": null,
  "created_at": "2026-02-17T09:54:44Z"
}
```

**Error Responses:**
- `400 Bad Request` - Deal not active or user reached max uses
- `401 Unauthorized` - User not authenticated

---

### 2. Merchant Redeems Deal (Merchant App)

**Endpoint:** `POST /merchant/api/deals/redeem`

**Authentication:** Required (Merchant/Restaurant token)

**Request Body (Option 1 - QR Scan):**
```json
{
  "qr_data": "DEALUSE:105:123456"
}
```

**Request Body (Option 2 - Manual Code Entry):**
```json
{
  "redemption_code": "123456"
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "reason": "Deal redeemed successfully.",
  "id": 105,
  "deal": {
    "id": 42,
    "title": "50% Off Main Course",
    "description": "Get 50% discount on any main course",
    "deal_type": "percentage",
    "discount_percentage": 50.0,
    "discount_amount": null,
    "restaurant_name": "The Italian Place",
    "restaurant_slug": "the-italian-place",
    "city_name": "Mumbai"
  },
  "used_at": "2026-02-17T09:54:44Z",
  "restaurant_confirmed": true,
  "notes": "",
  "redemption_code": "123456",
  "qr_code": "/media/qr_codes/qr_105.png",
  "qr_code_url": "https://api.example.com/media/qr_codes/qr_105.png",
  "is_redeemed": true,
  "redeemed_at": "2026-02-17T10:15:30Z",
  "created_at": "2026-02-17T09:54:44Z"
}
```

**Error Responses:**

**400 Bad Request** - Invalid request:
```json
{
  "success": false,
  "reason": "Redemption not found."
}
```

**400 Bad Request** - Deal no longer valid:
```json
{
  "success": false,
  "reason": "This deal is no longer valid."
}
```

**403 Forbidden** - Not authorized:
```json
{
  "success": false,
  "reason": "You are not allowed to redeem deals for this restaurant."
}
```

**409 Conflict** - Already redeemed:
```json
{
  "success": false,
  "reason": "This deal has already been redeemed."
}
```

---

## Flutter Implementation

### Step 1: Add Dependencies

Add these packages to your `pubspec.yaml`:

```yaml
dependencies:
  # QR Code scanning
  mobile_scanner: ^5.0.0  # Modern QR scanner with better performance
  
  # Permissions
  permission_handler: ^11.0.0
  
  # HTTP requests (if not already added)
  http: ^1.0.0
```

### Step 2: Update Permissions

**Android** (`android/app/src/main/AndroidManifest.xml`):
```xml
<uses-permission android:name="android.permission.CAMERA" />
<uses-feature android:name="android.hardware.camera" />
<uses-feature android:name="android.hardware.camera.autofocus" />
```

**iOS** (`ios/Runner/Info.plist`):
```xml
<key>NSCameraUsageDescription</key>
<string>We need camera access to scan QR codes for deal redemption</string>
```

### Step 3: Create QR Scanner Service

```dart
// lib/services/qr_scanner_service.dart

import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:permission_handler/permission_handler.dart';

class QRScannerService {
  /// Request camera permission
  static Future<bool> requestCameraPermission() async {
    final status = await Permission.camera.request();
    return status.isGranted;
  }

  /// Check if camera permission is granted
  static Future<bool> hasCameraPermission() async {
    final status = await Permission.camera.status;
    return status.isGranted;
  }

  /// Validate QR code format
  static bool isValidDealQRCode(String qrData) {
    if (qrData.isEmpty) return false;
    
    final parts = qrData.split(':');
    if (parts.length != 3) return false;
    if (parts[0] != 'DEALUSE') return false;
    
    // Validate ID is numeric
    if (int.tryParse(parts[1]) == null) return false;
    
    // Validate redemption code is 6 digits
    if (parts[2].length != 6 || int.tryParse(parts[2]) == null) return false;
    
    return true;
  }

  /// Extract deal use ID from QR data
  static int? extractDealUseId(String qrData) {
    if (!isValidDealQRCode(qrData)) return null;
    final parts = qrData.split(':');
    return int.tryParse(parts[1]);
  }

  /// Extract redemption code from QR data
  static String? extractRedemptionCode(String qrData) {
    if (!isValidDealQRCode(qrData)) return null;
    final parts = qrData.split(':');
    return parts[2];
  }
}
```

### Step 4: Create Redemption API Service

```dart
// lib/services/deal_redemption_service.dart

import 'package:dio/dio.dart';
import '../models/deal_use.dart';

class DealRedemptionService {
  final Dio _dio;
  final String baseUrl;

  DealRedemptionService(this._dio, {required this.baseUrl});

  /// Redeem deal using QR data
  Future<RedemptionResult> redeemDealByQR(String qrData) async {
    try {
      final response = await _dio.post(
        '$baseUrl/merchant/api/deals/redeem',
        data: {'qr_data': qrData},
      );

      if (response.statusCode == 200) {
        return RedemptionResult.success(
          dealUse: DealUse.fromJson(response.data),
          message: response.data['reason'] ?? 'Deal redeemed successfully',
        );
      }

      return RedemptionResult.failure(
        message: 'Unexpected response from server',
      );
    } on DioException catch (e) {
      return _handleError(e);
    }
  }

  /// Redeem deal using manual code entry
  Future<RedemptionResult> redeemDealByCode(String redemptionCode) async {
    try {
      final response = await _dio.post(
        '$baseUrl/merchant/api/deals/redeem',
        data: {'redemption_code': redemptionCode},
      );

      if (response.statusCode == 200) {
        return RedemptionResult.success(
          dealUse: DealUse.fromJson(response.data),
          message: response.data['reason'] ?? 'Deal redeemed successfully',
        );
      }

      return RedemptionResult.failure(
        message: 'Unexpected response from server',
      );
    } on DioException catch (e) {
      return _handleError(e);
    }
  }

  RedemptionResult _handleError(DioException e) {
    if (e.response != null) {
      final data = e.response!.data;
      final reason = data is Map ? data['reason'] : null;

      switch (e.response!.statusCode) {
        case 400:
          return RedemptionResult.failure(
            message: reason ?? 'Invalid redemption code or QR data',
            errorType: RedemptionErrorType.invalidCode,
          );
        case 403:
          return RedemptionResult.failure(
            message: reason ?? 'You are not authorized to redeem this deal',
            errorType: RedemptionErrorType.unauthorized,
          );
        case 409:
          return RedemptionResult.failure(
            message: reason ?? 'This deal has already been redeemed',
            errorType: RedemptionErrorType.alreadyRedeemed,
          );
        default:
          return RedemptionResult.failure(
            message: reason ?? 'Failed to redeem deal',
          );
      }
    }

    return RedemptionResult.failure(
      message: 'Network error. Please check your connection.',
      errorType: RedemptionErrorType.networkError,
    );
  }
}

// Models
class RedemptionResult {
  final bool success;
  final String message;
  final DealUse? dealUse;
  final RedemptionErrorType? errorType;

  RedemptionResult.success({
    required this.dealUse,
    required this.message,
  })  : success = true,
        errorType = null;

  RedemptionResult.failure({
    required this.message,
    this.errorType,
  })  : success = false,
        dealUse = null;
}

enum RedemptionErrorType {
  invalidCode,
  alreadyRedeemed,
  unauthorized,
  networkError,
  dealExpired,
}
```

### Step 5: Create QR Scanner Screen

```dart
// lib/screens/merchant/qr_scanner_screen.dart

import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import '../../services/qr_scanner_service.dart';
import '../../services/deal_redemption_service.dart';

class QRScannerScreen extends StatefulWidget {
  const QRScannerScreen({Key? key}) : super(key: key);

  @override
  State<QRScannerScreen> createState() => _QRScannerScreenState();
}

class _QRScannerScreenState extends State<QRScannerScreen> {
  final MobileScannerController _controller = MobileScannerController();
  bool _isProcessing = false;
  bool _hasPermission = false;

  @override
  void initState() {
    super.initState();
    _checkPermission();
  }

  Future<void> _checkPermission() async {
    final hasPermission = await QRScannerService.hasCameraPermission();
    if (!hasPermission) {
      final granted = await QRScannerService.requestCameraPermission();
      setState(() => _hasPermission = granted);
    } else {
      setState(() => _hasPermission = true);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _handleQRCode(String qrData) async {
    if (_isProcessing) return;

    setState(() => _isProcessing = true);

    // Validate QR format
    if (!QRScannerService.isValidDealQRCode(qrData)) {
      _showError('Invalid QR code format');
      setState(() => _isProcessing = false);
      return;
    }

    // Show loading
    _showLoadingDialog();

    // Call redemption API
    final redemptionService = DealRedemptionService(
      // Inject your Dio instance here
      Dio(),
      baseUrl: 'https://your-api-url.com',
    );

    final result = await redemptionService.redeemDealByQR(qrData);

    // Hide loading
    Navigator.of(context).pop();

    if (result.success) {
      _showSuccessDialog(result.dealUse!);
    } else {
      _showErrorDialog(result.message, result.errorType);
    }

    setState(() => _isProcessing = false);
  }

  void _showLoadingDialog() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const Center(
        child: CircularProgressIndicator(),
      ),
    );
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
      ),
    );
  }

  void _showSuccessDialog(DealUse dealUse) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Row(
          children: [
            Icon(Icons.check_circle, color: Colors.green, size: 32),
            SizedBox(width: 12),
            Text('Deal Redeemed!'),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              dealUse.deal.title,
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            Text('Code: ${dealUse.redemptionCode}'),
            const SizedBox(height: 4),
            Text('Redeemed at: ${_formatDateTime(dealUse.redeemedAt)}'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
              Navigator.of(context).pop(); // Go back to previous screen
            },
            child: const Text('Done'),
          ),
        ],
      ),
    );
  }

  void _showErrorDialog(String message, RedemptionErrorType? errorType) {
    IconData icon = Icons.error;
    Color color = Colors.red;

    if (errorType == RedemptionErrorType.alreadyRedeemed) {
      icon = Icons.warning;
      color = Colors.orange;
    }

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Row(
          children: [
            Icon(icon, color: color, size: 32),
            const SizedBox(width: 12),
            const Text('Redemption Failed'),
          ],
        ),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  String _formatDateTime(DateTime? dateTime) {
    if (dateTime == null) return 'N/A';
    return '${dateTime.day}/${dateTime.month}/${dateTime.year} ${dateTime.hour}:${dateTime.minute.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    if (!_hasPermission) {
      return Scaffold(
        appBar: AppBar(title: const Text('Scan QR Code')),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.camera_alt, size: 64, color: Colors.grey),
              const SizedBox(height: 16),
              const Text(
                'Camera permission required',
                style: TextStyle(fontSize: 18),
              ),
              const SizedBox(height: 24),
              ElevatedButton(
                onPressed: _checkPermission,
                child: const Text('Grant Permission'),
              ),
            ],
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Scan QR Code'),
        actions: [
          IconButton(
            icon: const Icon(Icons.keyboard),
            onPressed: () => _showManualEntryDialog(),
            tooltip: 'Enter code manually',
          ),
        ],
      ),
      body: Stack(
        children: [
          MobileScanner(
            controller: _controller,
            onDetect: (capture) {
              final List<Barcode> barcodes = capture.barcodes;
              for (final barcode in barcodes) {
                if (barcode.rawValue != null) {
                  _handleQRCode(barcode.rawValue!);
                  break;
                }
              }
            },
          ),
          // Overlay with scanning frame
          CustomPaint(
            painter: ScannerOverlayPainter(),
            child: Container(),
          ),
          // Instructions
          Positioned(
            bottom: 100,
            left: 0,
            right: 0,
            child: Container(
              padding: const EdgeInsets.all(16),
              color: Colors.black54,
              child: const Text(
                'Position the QR code within the frame',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 16,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _showManualEntryDialog() {
    final controller = TextEditingController();

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Enter Redemption Code'),
        content: TextField(
          controller: controller,
          keyboardType: TextInputType.number,
          maxLength: 6,
          decoration: const InputDecoration(
            hintText: '6-digit code',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              final code = controller.text.trim();
              if (code.length != 6) {
                _showError('Code must be 6 digits');
                return;
              }

              Navigator.of(context).pop();
              _showLoadingDialog();

              final redemptionService = DealRedemptionService(
                Dio(),
                baseUrl: 'https://your-api-url.com',
              );

              final result = await redemptionService.redeemDealByCode(code);
              Navigator.of(context).pop();

              if (result.success) {
                _showSuccessDialog(result.dealUse!);
              } else {
                _showErrorDialog(result.message, result.errorType);
              }
            },
            child: const Text('Redeem'),
          ),
        ],
      ),
    );
  }
}

// Custom painter for scanner overlay
class ScannerOverlayPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.black54
      ..style = PaintingStyle.fill;

    final framePaint = Paint()
      ..color = Colors.white
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3;

    final frameSize = size.width * 0.7;
    final left = (size.width - frameSize) / 2;
    final top = (size.height - frameSize) / 2;

    // Draw semi-transparent overlay
    canvas.drawPath(
      Path()
        ..addRect(Rect.fromLTWH(0, 0, size.width, size.height))
        ..addRect(Rect.fromLTWH(left, top, frameSize, frameSize))
        ..fillType = PathFillType.evenOdd,
      paint,
    );

    // Draw frame corners
    final cornerLength = 30.0;
    final rect = Rect.fromLTWH(left, top, frameSize, frameSize);

    // Top-left
    canvas.drawLine(
      Offset(rect.left, rect.top),
      Offset(rect.left + cornerLength, rect.top),
      framePaint,
    );
    canvas.drawLine(
      Offset(rect.left, rect.top),
      Offset(rect.left, rect.top + cornerLength),
      framePaint,
    );

    // Top-right
    canvas.drawLine(
      Offset(rect.right, rect.top),
      Offset(rect.right - cornerLength, rect.top),
      framePaint,
    );
    canvas.drawLine(
      Offset(rect.right, rect.top),
      Offset(rect.right, rect.top + cornerLength),
      framePaint,
    );

    // Bottom-left
    canvas.drawLine(
      Offset(rect.left, rect.bottom),
      Offset(rect.left + cornerLength, rect.bottom),
      framePaint,
    );
    canvas.drawLine(
      Offset(rect.left, rect.bottom),
      Offset(rect.left, rect.bottom - cornerLength),
      framePaint,
    );

    // Bottom-right
    canvas.drawLine(
      Offset(rect.right, rect.bottom),
      Offset(rect.right - cornerLength, rect.bottom),
      framePaint,
    );
    canvas.drawLine(
      Offset(rect.right, rect.bottom),
      Offset(rect.right, rect.bottom - cornerLength),
      framePaint,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
```

---

## Testing Guide

### Test Cases

1. **Valid QR Code Scan**
   - Scan a valid QR code
   - Verify redemption success message
   - Check deal is marked as redeemed

2. **Already Redeemed Deal**
   - Scan the same QR code twice
   - Verify 409 error with appropriate message

3. **Invalid QR Code**
   - Scan a random QR code
   - Verify validation error

4. **Manual Code Entry**
   - Enter 6-digit code manually
   - Verify redemption works

5. **Network Error**
   - Turn off network
   - Verify error handling

6. **Permission Denied**
   - Deny camera permission
   - Verify permission request flow

---

## Security Considerations

1. **Authentication**: Always verify merchant is authenticated before allowing redemption
2. **Authorization**: Backend validates merchant owns the restaurant
3. **Unique Codes**: 6-digit codes are unique across all DealUse records
4. **One-Time Use**: QR codes can only be redeemed once
5. **Expiration**: Backend validates deal is still active

---

## Troubleshooting

### Common Issues

**Issue**: QR scanner not working on iOS
- **Solution**: Ensure `NSCameraUsageDescription` is added to Info.plist

**Issue**: "Invalid QR data format" error
- **Solution**: Verify QR contains exactly 3 parts separated by colons

**Issue**: 403 Unauthorized error
- **Solution**: Ensure merchant user is logged in and owns the restaurant

**Issue**: QR code image not loading
- **Solution**: Check media URL configuration in backend settings

---

## Additional Features (Optional)

### 1. Redemption History
Track all redemptions for analytics:
```dart
GET /merchant/api/deals/redemptions?date=2026-02-17
```

### 2. Offline Support
Cache redemption requests when offline and sync later

### 3. Sound/Vibration Feedback
Add haptic feedback on successful scan

### 4. Flashlight Toggle
Add button to toggle flashlight in low-light conditions

---

## Summary

This implementation provides a complete QR code redemption system with:
- ✅ QR code generation on deal claim
- ✅ QR scanner with camera permissions
- ✅ Manual code entry fallback
- ✅ Comprehensive error handling
- ✅ Success/failure feedback
- ✅ Security validation
- ✅ User-friendly UI

The merchant app can now scan customer QR codes and redeem deals seamlessly!
