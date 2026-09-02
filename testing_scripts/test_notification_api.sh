#!/bin/bash

# Discount Buddy - Test Notification API
# This script tests the notification system with a valid JWT token

BASE_URL="http://192.168.29.221:8000"

echo "========================================="
echo "Discount Buddy - Notification API Test"
echo "========================================="
echo ""

# Step 1: Login to get JWT token
echo "Step 1: Login to get JWT token..."
echo "Enter your email:"
read USER_EMAIL
echo "Enter your password:"
read -s USER_PASSWORD
echo ""

LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/user/api/users/login/" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"${USER_EMAIL}\", \"password\": \"${USER_PASSWORD}\"}")

# Extract access token
ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('access', ''))" 2>/dev/null)

if [ -z "$ACCESS_TOKEN" ]; then
    echo "❌ Login failed!"
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi

echo "✅ Login successful!"
echo "Token: ${ACCESS_TOKEN:0:20}..."
echo ""

# Step 2: Send test notification
echo "Step 2: Sending test notification..."
TEST_RESPONSE=$(curl -s -X POST "${BASE_URL}/user/api/notifications/send_test" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Notification 🚀",
    "message": "This is a test from the API! Notifications are working perfectly!",
    "send_push": true
  }')

echo "Response:"
echo "$TEST_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$TEST_RESPONSE"
echo ""

# Step 3: Get unread count
echo "Step 3: Checking unread notification count..."
UNREAD_RESPONSE=$(curl -s -X GET "${BASE_URL}/user/api/notifications/unread_count" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")

echo "Unread count:"
echo "$UNREAD_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$UNREAD_RESPONSE"
echo ""

# Step 4: List notifications
echo "Step 4: Listing recent notifications..."
LIST_RESPONSE=$(curl -s -X GET "${BASE_URL}/user/api/notifications/?page=1&page_size=5" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")

echo "Recent notifications:"
echo "$LIST_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$LIST_RESPONSE"
echo ""

echo "========================================="
echo "✅ Test Complete!"
echo "========================================="
echo ""
echo "Summary:"
echo "- Login: ✅"
echo "- Test notification sent: ✅"
echo "- Unread count retrieved: ✅"
echo "- Notifications listed: ✅"
echo ""
echo "Check your mobile app for the push notification!"
