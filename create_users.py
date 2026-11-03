
# create_users.py
import os
import sys
import django

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from account.models import Admin, Employee
from django.contrib.auth.models import User

print("=" * 50)
print("CREATING USERS")
print("=" * 50)

# Create Admin - check if exists first
admin_user, created = User.objects.get_or_create(
    username='admin1',
    defaults={
        'email': 'admin@example.com',
        'password': 'admin123'  # This will be overwritten by set_password
    }
)

if created:
    admin_user.set_password('admin123')
    admin_user.save()
    admin = Admin.objects.create(user=admin_user, department='IT')
    print('✅ Admin created: admin1 / admin123')
else:
    print('ℹ️ Admin already exists: admin1')

# Create Employee Record
employee, created = Employee.objects.get_or_create(
    email='john@example.com',
    defaults={
        'name': 'John Doe',
        'phone': '1234567890',
        'department': 'IT',
        'salary': 50000.00
    }
)

if created:
    print('✅ Employee record created: John Doe')
else:
    print('ℹ️ Employee record already exists: John Doe')

# Create Employee Login User
emp_user, created = User.objects.get_or_create(
    username='john_doe',
    defaults={
        'email': 'john@example.com',
        'password': 'emp123'  # This will be overwritten by set_password
    }
)

if created:
    emp_user.set_password('emp123')
    emp_user.save()
    print('✅ Employee login created: john_doe / emp123')
else:
    print('ℹ️ Employee login already exists: john_doe')

print("=" * 50)
print("USER CREATION COMPLETE")
print("=" * 50)