import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from donations.models import SiteSettings


class Command(BaseCommand):
    help = "Create settings row and admin user from environment variables."

    def handle(self, *args, **options):
        site = SiteSettings.load()
        site.min_amount_toman = 10_000
        site.max_amount_toman = 100_000_000
        site.save(update_fields=["min_amount_toman", "max_amount_toman"])
        username = os.getenv("ADMIN_USERNAME", "admin")
        password = os.getenv("ADMIN_PASSWORD", "")
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"is_staff": True, "is_superuser": True, "email": ""},
        )
        user.is_staff = True
        user.is_superuser = True
        if password:
            user.set_password(password)
            self.stdout.write(self.style.SUCCESS(f"Admin password set for '{username}'."))
        elif created:
            user.set_password("admin1234")
            self.stdout.write(self.style.WARNING("ADMIN_PASSWORD خالی بود؛ رمز موقت admin1234 گذاشته شد. عوضش کن."))
        user.save()
        self.stdout.write(self.style.SUCCESS("Bootstrap done."))
