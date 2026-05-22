from django.core.management.base import BaseCommand

from restaurants.models import Restaurant
from restaurants.opening_hours_sync import sync_opening_slots_from_opening_hours


class Command(BaseCommand):
    help = "Backfill OpeningSlot rows from Restaurant.opening_hours JSON."

    def add_arguments(self, parser):
        parser.add_argument(
            "--restaurant-id",
            type=int,
            help="Sync only this restaurant ID.",
        )

    def handle(self, *args, **options):
        queryset = Restaurant.objects.all()
        restaurant_id = options.get("restaurant_id")
        if restaurant_id:
            queryset = queryset.filter(id=restaurant_id)

        total_restaurants = 0
        total_days = 0

        for restaurant in queryset.iterator():
            hours = restaurant.opening_hours or {}
            if not hours:
                continue
            days = sync_opening_slots_from_opening_hours(restaurant)
            if days:
                total_restaurants += 1
                total_days += days
                self.stdout.write(
                    f"Synced {days} day(s) for restaurant {restaurant.id} ({restaurant.name})"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Updated slots for {total_restaurants} restaurant(s), "
                f"{total_days} day slot(s) in total."
            )
        )
