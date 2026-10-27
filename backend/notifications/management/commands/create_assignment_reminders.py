import os

from django.core.management.base import BaseCommand, CommandError

from notifications.reminders import create_assignment_reminders


class Command(BaseCommand):
    help = "Create in-app reminders for assignments due within the next 24 hours."

    def handle(self, *args, **options):
        if not os.getenv("DATABASE_URL"):
            raise CommandError("DATABASE_URL must point to the production PostgreSQL database.")

        created_count, _ = create_assignment_reminders()
        self.stdout.write(self.style.SUCCESS(f"Created or activated {created_count} assignment reminder(s)."))
