"""Create (or update) the first admin login from environment variables.

Usage:  python manage.py create_admin
Env:    ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_EMAIL (optional)
Safe to run on every deploy: it does nothing if the variables are not set.
"""
import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from account.models import Admin


class Command(BaseCommand):
    help = "Create the initial admin user from ADMIN_USERNAME / ADMIN_PASSWORD env vars."

    def handle(self, *args, **options):
        username = os.environ.get('ADMIN_USERNAME')
        password = os.environ.get('ADMIN_PASSWORD')
        if not username or not password:
            self.stdout.write('ADMIN_USERNAME / ADMIN_PASSWORD not set - skipping.')
            return

        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': os.environ.get('ADMIN_EMAIL', ''), 'is_staff': True, 'is_superuser': True},
        )
        if created:
            user.set_password(password)
            user.save()
        Admin.objects.get_or_create(user=user, defaults={'department': 'IT'})
        self.stdout.write(self.style.SUCCESS(
            f"Admin '{username}' created." if created else f"Admin '{username}' already exists."))
