"""
Management command to create dummy data for testing all APIs
Run: python manage.py create_dummy_data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import random

from restaurants.models import (
    Country, City, RestaurantCategory, Cuisine, Restaurant,
    RestaurantImage, Deal, DealImage, Review, Booking,
    MenuCategory, MenuItem, OpeningSlot, RestaurantProfile,
    SavedRestaurant, SavedDeal, DealUse
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Create dummy data for testing all APIs'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating dummy data...'))
        
        # Create superuser if doesn't exist
        if not User.objects.filter(is_superuser=True).exists():
            superuser = User.objects.create_superuser(
                email='admin@discountbuddy.com',
                username='admin',
                password='admin123'
            )
            self.stdout.write(self.style.SUCCESS(f'Created superuser: {superuser.email}'))
        else:
            self.stdout.write(self.style.WARNING('Superuser already exists'))
        
        # Create regular users
        users = []
        for i in range(5):
            user, created = User.objects.get_or_create(
                email=f'user{i+1}@test.com',
                defaults={
                    'username': f'user{i+1}',
                    'is_customer': True
                }
            )
            if created:
                user.set_password('test123')
                user.save()
            users.append(user)
        self.stdout.write(self.style.SUCCESS(f'Created {len(users)} users'))
        
        # Create Countries
        countries_data = [
            {'name': 'United Kingdom', 'code': 'GB', 'flag_emoji': '🇬🇧'},
            {'name': 'United States', 'code': 'US', 'flag_emoji': '🇺🇸'},
            {'name': 'India', 'code': 'IN', 'flag_emoji': '🇮🇳'},
        ]
        countries = []
        for country_data in countries_data:
            country, _ = Country.objects.get_or_create(**country_data)
            countries.append(country)
        self.stdout.write(self.style.SUCCESS(f'Created {len(countries)} countries'))
        
        # Create Cities
        cities_data = [
            {'name': 'London', 'country': countries[0], 'slug': 'london', 'latitude': 51.5074, 'longitude': -0.1278},
            {'name': 'Manchester', 'country': countries[0], 'slug': 'manchester', 'latitude': 53.4808, 'longitude': -2.2426},
            {'name': 'New York', 'country': countries[1], 'slug': 'new-york', 'latitude': 40.7128, 'longitude': -74.0060},
            {'name': 'Mumbai', 'country': countries[2], 'slug': 'mumbai', 'latitude': 19.0760, 'longitude': 72.8777},
        ]
        cities = []
        for city_data in cities_data:
            city, _ = City.objects.get_or_create(
                name=city_data['name'],
                country=city_data['country'],
                defaults={
                    'slug': city_data['slug'],
                    'latitude': city_data['latitude'],
                    'longitude': city_data['longitude']
                }
            )
            cities.append(city)
        self.stdout.write(self.style.SUCCESS(f'Created {len(cities)} cities'))
        
        # Create Restaurant Categories
        categories_data = [
            {'name': 'Fine Dining', 'slug': 'fine-dining', 'icon': '🍽️'},
            {'name': 'Casual Dining', 'slug': 'casual-dining', 'icon': '🍴'},
            {'name': 'Fast Food', 'slug': 'fast-food', 'icon': '🍔'},
            {'name': 'Cafe', 'slug': 'cafe', 'icon': '☕'},
            {'name': 'Bar & Grill', 'slug': 'bar-grill', 'icon': '🍻'},
        ]
        categories = []
        for cat_data in categories_data:
            category, _ = RestaurantCategory.objects.get_or_create(**cat_data)
            categories.append(category)
        self.stdout.write(self.style.SUCCESS(f'Created {len(categories)} restaurant categories'))
        
        # Create Cuisines
        cuisines_data = [
            {'name': 'Italian', 'slug': 'italian', 'icon': '🍝'},
            {'name': 'Chinese', 'slug': 'chinese', 'icon': '🥢'},
            {'name': 'Indian', 'slug': 'indian', 'icon': '🍛'},
            {'name': 'Mexican', 'slug': 'mexican', 'icon': '🌮'},
            {'name': 'Japanese', 'slug': 'japanese', 'icon': '🍣'},
            {'name': 'American', 'slug': 'american', 'icon': '🍔'},
        ]
        cuisines = []
        for cuisine_data in cuisines_data:
            cuisine, _ = Cuisine.objects.get_or_create(**cuisine_data)
            cuisines.append(cuisine)
        self.stdout.write(self.style.SUCCESS(f'Created {len(cuisines)} cuisines'))
        
        # Create Restaurants
        restaurants_data = [
            {
                'name': 'The Golden Fork',
                'slug': 'the-golden-fork',
                'description': 'Fine dining restaurant serving exquisite European cuisine',
                'city': cities[0],
                'address': '123 High Street, London',
                'postcode': 'SW1A 1AA',
                'latitude': 51.5074,
                'longitude': -0.1278,
                'phone': '+44 20 1234 5678',
                'email': 'info@goldenfork.com',
                'website': 'https://goldenfork.com',
                'price_range': 4,
                'verified': True,
                'is_featured': True,
            },
            {
                'name': 'Spice Garden',
                'slug': 'spice-garden',
                'description': 'Authentic Indian cuisine with modern twists',
                'city': cities[0],
                'address': '456 Oxford Street, London',
                'postcode': 'W1D 1BS',
                'latitude': 51.5150,
                'longitude': -0.1419,
                'phone': '+44 20 2345 6789',
                'email': 'hello@spicegarden.com',
                'price_range': 3,
                'verified': True,
                'is_featured': True,
            },
            {
                'name': 'Bella Italia',
                'slug': 'bella-italia',
                'description': 'Traditional Italian pizzeria and pasta house',
                'city': cities[1],
                'address': '789 Market Street, Manchester',
                'postcode': 'M1 1AA',
                'latitude': 53.4808,
                'longitude': -2.2426,
                'phone': '+44 161 3456 7890',
                'email': 'info@bellaitalia.com',
                'price_range': 2,
                'verified': True,
                'is_featured': False,
            },
            {
                'name': 'Dragon Palace',
                'slug': 'dragon-palace',
                'description': 'Authentic Chinese cuisine in the heart of the city',
                'city': cities[2],
                'address': '321 Broadway, New York',
                'postcode': '10001',
                'latitude': 40.7128,
                'longitude': -74.0060,
                'phone': '+1 212 456 7890',
                'email': 'info@dragonpalace.com',
                'price_range': 2,
                'verified': True,
                'is_featured': False,
            },
            {
                'name': 'Mumbai Spice',
                'slug': 'mumbai-spice',
                'description': 'Best Indian street food and traditional dishes',
                'city': cities[3],
                'address': '555 Marine Drive, Mumbai',
                'postcode': '400001',
                'latitude': 19.0760,
                'longitude': 72.8777,
                'phone': '+91 22 5678 9012',
                'email': 'info@mumbaispice.com',
                'price_range': 1,
                'verified': True,
                'is_featured': False,
            },
        ]
        
        restaurants = []
        for rest_data in restaurants_data:
            city = rest_data.pop('city')
            restaurant, _ = Restaurant.objects.get_or_create(
                slug=rest_data['slug'],
                defaults={**rest_data, 'city': city}
            )
            # Add random categories and cuisines
            restaurant.categories.set(random.sample(categories, random.randint(1, 3)))
            restaurant.cuisines.set(random.sample(cuisines, random.randint(1, 2)))
            restaurants.append(restaurant)
        self.stdout.write(self.style.SUCCESS(f'Created {len(restaurants)} restaurants'))
        
        # Create Restaurant Images
        for restaurant in restaurants:
            for i in range(random.randint(2, 4)):
                RestaurantImage.objects.get_or_create(
                    restaurant=restaurant,
                    defaults={
                        'alt_text': f'{restaurant.name} - Image {i+1}',
                        'is_primary': i == 0,
                        'order': i
                    }
                )
        self.stdout.write(self.style.SUCCESS('Created restaurant images'))
        
        # Create Opening Slots
        days = [0, 1, 2, 3, 4, 5, 6]  # Monday to Sunday
        for restaurant in restaurants:
            for day in days:
                if day < 5:  # Monday to Friday
                    OpeningSlot.objects.get_or_create(
                        restaurant=restaurant,
                        day_of_week=day,
                        defaults={
                            'opening_time': '09:00',
                            'closing_time': '22:00',
                            'is_closed': False
                        }
                    )
                elif day == 5:  # Saturday
                    OpeningSlot.objects.get_or_create(
                        restaurant=restaurant,
                        day_of_week=day,
                        defaults={
                            'opening_time': '10:00',
                            'closing_time': '23:00',
                            'is_closed': False
                        }
                    )
                else:  # Sunday
                    OpeningSlot.objects.get_or_create(
                        restaurant=restaurant,
                        day_of_week=day,
                        defaults={
                            'opening_time': '11:00',
                            'closing_time': '21:00',
                            'is_closed': False
                        }
                    )
        self.stdout.write(self.style.SUCCESS('Created opening slots'))
        
        # Create Menu Categories and Items
        menu_category_names = ['Appetizers', 'Main Course', 'Desserts', 'Beverages']
        for restaurant in restaurants:
            for idx, cat_name in enumerate(menu_category_names):
                menu_cat, _ = MenuCategory.objects.get_or_create(
                    restaurant=restaurant,
                    name=cat_name,
                    defaults={
                        'description': f'{cat_name} menu',
                        'order': idx,
                        'is_active': True
                    }
                )
                
                # Create menu items for each category
                if cat_name == 'Appetizers':
                    items = [
                        {'name': 'Garlic Bread', 'price': 5.99, 'description': 'Fresh baked bread with garlic butter'},
                        {'name': 'Caesar Salad', 'price': 8.99, 'description': 'Fresh romaine lettuce with caesar dressing'},
                    ]
                elif cat_name == 'Main Course':
                    items = [
                        {'name': 'Grilled Chicken', 'price': 18.99, 'description': 'Tender grilled chicken breast'},
                        {'name': 'Beef Steak', 'price': 24.99, 'description': 'Prime cut beef steak'},
                        {'name': 'Vegetable Pasta', 'price': 14.99, 'description': 'Fresh pasta with vegetables', 'is_vegetarian': True},
                    ]
                elif cat_name == 'Desserts':
                    items = [
                        {'name': 'Chocolate Cake', 'price': 7.99, 'description': 'Rich chocolate cake'},
                        {'name': 'Ice Cream', 'price': 5.99, 'description': 'Vanilla ice cream', 'is_vegetarian': True},
                    ]
                else:  # Beverages
                    items = [
                        {'name': 'Coca Cola', 'price': 2.99, 'description': 'Soft drink'},
                        {'name': 'Fresh Juice', 'price': 4.99, 'description': 'Fresh orange juice', 'is_vegetarian': True},
                    ]
                
                for item_data in items:
                    MenuItem.objects.get_or_create(
                        category=menu_cat,
                        name=item_data['name'],
                        defaults={
                            'description': item_data.get('description', ''),
                            'price': item_data['price'],
                            'is_vegetarian': item_data.get('is_vegetarian', False),
                            'is_available': True,
                            'order': items.index(item_data)
                        }
                    )
        self.stdout.write(self.style.SUCCESS('Created menu categories and items'))
        
        # Create Deals
        deals_data = []
        for restaurant in restaurants:
            for i in range(random.randint(2, 4)):
                start_date = timezone.now() - timedelta(days=random.randint(0, 5))
                end_date = timezone.now() + timedelta(days=random.randint(10, 30))
                
                deal_type = random.choice(['percentage', 'fixed', 'two_for_one'])
                deal_data = {
                    'restaurant': restaurant,
                    'title': f'{restaurant.name} Special Offer {i+1}',
                    'description': f'Great deal at {restaurant.name}!',
                    'deal_type': deal_type,
                    'start_date': start_date,
                    'end_date': end_date,
                    'is_featured': i == 0,
                }
                
                if deal_type == 'percentage':
                    deal_data['discount_percentage'] = random.choice([10, 15, 20, 25, 30])
                elif deal_type == 'fixed':
                    deal_data['discount_amount'] = random.choice([5, 10, 15, 20])
                
                deal_data['minimum_spend'] = random.choice([None, 20, 30, 50])
                deal_data['max_uses'] = random.choice([None, 100, 200])
                deal_data['max_per_user'] = random.randint(1, 3)
                deal_data['terms_and_conditions'] = 'Valid for dine-in only. Cannot be combined with other offers.'
                
                deal, _ = Deal.objects.get_or_create(
                    restaurant=restaurant,
                    title=deal_data['title'],
                    defaults=deal_data
                )
                deals_data.append(deal)
        self.stdout.write(self.style.SUCCESS(f'Created {len(deals_data)} deals'))
        
        # Create Deal Images
        for deal in deals_data:
            DealImage.objects.get_or_create(
                deal=deal,
                defaults={
                    'alt_text': f'{deal.title} image',
                    'is_primary': True,
                    'order': 0
                }
            )
        self.stdout.write(self.style.SUCCESS('Created deal images'))
        
        # Create Reviews
        for restaurant in restaurants:
            for user in users[:3]:  # First 3 users review each restaurant
                rating = random.randint(3, 5)
                comments = [
                    'Great food and service!',
                    'Amazing experience, will come again.',
                    'Good value for money.',
                    'Excellent quality, highly recommended.',
                    'Nice ambiance and friendly staff.',
                ]
                Review.objects.get_or_create(
                    user=user,
                    restaurant=restaurant,
                    defaults={
                        'rating': rating,
                        'comment': random.choice(comments),
                        'is_verified': random.choice([True, False])
                    }
                )
        self.stdout.write(self.style.SUCCESS('Created reviews'))
        
        # Create Bookings
        for restaurant in restaurants:
            for user in users:
                booking_date = timezone.now() + timedelta(days=random.randint(1, 14))
                Booking.objects.get_or_create(
                    user=user,
                    restaurant=restaurant,
                    booking_date=booking_date,
                    defaults={
                        'number_of_guests': random.randint(2, 6),
                        'status': random.choice(['pending', 'confirmed', 'confirmed']),
                        'contact_name': f'{user.username}',
                        'contact_phone': f'+44 7{random.randint(100000000, 999999999)}',
                        'special_requests': random.choice(['', 'Window seat please', 'Birthday celebration', ''])
                    }
                )
        self.stdout.write(self.style.SUCCESS('Created bookings'))
        
        # Create Saved Restaurants (Favourites)
        for user in users:
            saved_count = random.randint(2, 4)
            for restaurant in random.sample(restaurants, saved_count):
                SavedRestaurant.objects.get_or_create(
                    user=user,
                    restaurant=restaurant
                )
        self.stdout.write(self.style.SUCCESS('Created saved restaurants (favourites)'))
        
        # Create Saved Deals
        for user in users:
            saved_count = random.randint(1, 3)
            for deal in random.sample(deals_data, min(saved_count, len(deals_data))):
                SavedDeal.objects.get_or_create(
                    user=user,
                    deal=deal
                )
        self.stdout.write(self.style.SUCCESS('Created saved deals'))
        
        # Create Deal Uses (Claimed Deals)
        for user in users:
            used_count = random.randint(1, 3)
            for deal in random.sample(deals_data, min(used_count, len(deals_data))):
                if deal.is_active_now() and deal.can_user_use(user):
                    DealUse.objects.get_or_create(
                        user=user,
                        deal=deal,
                        defaults={
                            'used_at': timezone.now() - timedelta(days=random.randint(1, 30)),
                            'restaurant_confirmed': random.choice([True, False]),
                            'notes': random.choice(['', 'Great deal!', 'Will use again'])
                        }
                    )
        self.stdout.write(self.style.SUCCESS('Created deal uses (claimed deals)'))
        
        # Create Restaurant Profile (for restaurant owners)
        # Create a merchant user
        merchant_user, _ = User.objects.get_or_create(
            email='merchant@test.com',
            defaults={
                'username': 'merchant',
                'is_merchant': True,
                'is_customer': False
            }
        )
        if not merchant_user.password:
            merchant_user.set_password('test123')
            merchant_user.save()
        
        # Link merchant to first restaurant
        if restaurants:
            RestaurantProfile.objects.get_or_create(
                user=merchant_user,
                restaurant=restaurants[0],
                defaults={'is_primary_owner': True}
            )
        self.stdout.write(self.style.SUCCESS('Created restaurant profile'))
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('DUMMY DATA CREATION COMPLETE!'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(self.style.SUCCESS('\nLogin Credentials:'))
        self.stdout.write(self.style.SUCCESS('  Superuser: admin@discountbuddy.com / admin123'))
        self.stdout.write(self.style.SUCCESS('  Merchant: merchant@test.com / test123'))
        self.stdout.write(self.style.SUCCESS('  Users: user1@test.com to user5@test.com / test123'))
        self.stdout.write(self.style.SUCCESS('\nYou can now test all APIs!'))
