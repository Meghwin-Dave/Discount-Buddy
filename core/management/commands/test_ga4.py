from django.core.management.base import BaseCommand, CommandError

from core.services.google_analytics import GoogleAnalyticsService


class Command(BaseCommand):
    help = "Tests Google Analytics Data API connection"

    def handle(self, *args, **options):
        try:
            analytics = GoogleAnalyticsService()
            result = analytics.get_overview(start_date="7daysAgo", end_date="today")
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(str(result)))
