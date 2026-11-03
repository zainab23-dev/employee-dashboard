"""Create or update the Admin (HR), CEO and a sample Employee login from env vars."""
import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from account.models import Admin, Employee


def upsert_user(username, password, email, staff):
    user, created = User.objects.get_or_create(
        username=username,
        defaults={'email': email, 'is_staff': staff, 'is_superuser': staff},
    )
    user.set_password(password)
    if email:
        user.email = email
    user.save()
    return user, created


class Command(BaseCommand):
    help = "Create/update admin, CEO and employee logins from environment variables."

    def report(self, label, username, created):
        self.stdout.write(self.style.SUCCESS(
            f"{label} '{username}' {'created' if created else 'password updated'}."))

    def make_admin(self, prefix, role, label, department):
        username = os.environ.get(f'{prefix}_USERNAME')
        password = os.environ.get(f'{prefix}_PASSWORD')
        if not (username and password):
            self.stdout.write(f'{prefix}_USERNAME / {prefix}_PASSWORD not set - skipping {label}.')
            return
        user, created = upsert_user(username, password, os.environ.get(f'{prefix}_EMAIL', ''), True)
        admin, _ = Admin.objects.get_or_create(user=user, defaults={'department': department, 'role': role})
        if admin.role != role:
            admin.role = role
            admin.save()
        self.report(label, username, created)

    def make_employee(self):
        username = os.environ.get('EMPLOYEE_USERNAME')
        password = os.environ.get('EMPLOYEE_PASSWORD')
        if not (username and password):
            self.stdout.write('EMPLOYEE_USERNAME / EMPLOYEE_PASSWORD not set - skipping employee.')
            return
        email = os.environ.get('EMPLOYEE_EMAIL') or f'{username}@example.com'
        user, created = upsert_user(username, password, email, False)
        employee = Employee.objects.filter(email=email).first()
        if employee is None:
            employee = Employee.objects.create(
                user=user, name=os.environ.get('EMPLOYEE_NAME', username), email=email,
                phone='0000000000', department='General', salary=0)
        elif employee.user_id is None:
            employee.user = user
            employee.save()
        self.report('EMPLOYEE', username, created)

    def handle(self, *args, **options):
        self.make_admin('ADMIN', 'hr', 'HR admin', 'IT')
        self.make_admin('CEO', 'ceo', 'CEO', 'Management')
        self.make_employee()
