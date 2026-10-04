from django.core.management.base import BaseCommand

from apps.orders.services import release_expired


class Command(BaseCommand):
    help = "Put back the stock of unpaid orders past their deadline. The API also does it on read; run it from cron to keep lists tidy."

    def handle(self, *args, **options):
        count = release_expired()
        self.stdout.write(f"Released {count} expired order(s)")
