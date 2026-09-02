import os
import sys
from pathlib import Path

import django

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'discount_buddy.settings')
django.setup()

from notifications.services import NotificationService
from users.models import User
from restaurants.models import Booking, Restaurant

# Get a user and a restaurant
user = User.objects.first()
restaurant = Restaurant.objects.first()

if not user or not restaurant:
    print("No user or restaurant found")
    exit(1)

# Create a booking
booking = Booking.objects.create(
    user=user,
    restaurant=restaurant,
    booking_date="2026-04-01 19:30:00",
    number_of_guests=2,
    contact_name="Test User",
    status="pending"
)

print(f"Created booking {booking.id}")
