import os
import sys
from pathlib import Path

import django

# Set up Django environment
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'discount_buddy.settings')
django.setup()

from notifications.fcm import send_fcm_message

def send_test_booking_notification():
    token = "dhPYB5fouUP_tqvEwIlt9d:APA91bFE3j7LpxofH79aTetM2fVnthqjQXuTIfKVSontISsHnz2LPpdmiQXYfW_mmh6oUIHLepjYTXiRNHhAOHHrLWNwrO2eMv7nGA4d7D5Wy7kmTlme4xk"
    
    title = "New Table Booking Request 📅"
    customer_name = "Priyanshu Chavda"
    restaurant_name = "The Test Kitchen"
    guests = "2"
    booking_date = "April 25, 2026 at 08:30 PM"
    
    message = (
        f"{customer_name} has requested a table for {guests} guest(s) "
        f"at {restaurant_name} on {booking_date}."
    )
    
    payload = {
        "booking_id": "8939c388-6623-4554-ba5f-b51f044b68e9",
        "restaurant_id": "4020a112-9c9c-4464-9694-27510940562e",
        "customer_name": customer_name,
        "number_of_guests": guests,
        "booking_date": booking_date,
        "notification_type": "NEW_BOOKING"
    }
    
    print(f"--- Sending NEW_BOOKING notification to token ---")
    print(f"Token: {token[:20]}...")
    print(f"Title: {title}")
    print(f"Message: {message}")
    
    sent, error = send_fcm_message(
        token=token,
        title=title,
        body=message,
        data=payload
    )

    if sent:
        print("✅ Notification sent successfully!")
    else:
        print(f"❌ Failed to send notification: {error}")

if __name__ == "__main__":
    send_test_booking_notification()
