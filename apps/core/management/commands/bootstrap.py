from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create the database and fill it from data/*.csv, with a month of demo orders. Safe to run again to reset the demo."

    def add_arguments(self, parser):
        parser.add_argument("--no-demo-orders", action="store_true", help="Start with an empty order book.")

    def handle(self, *args, **options):
        call_command("migrate", interactive=False, verbosity=0)
        call_command("load_data")
        if not options["no_demo_orders"]:
            call_command("demo_orders")
