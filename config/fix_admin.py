# fix_admin.py
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from account.models import Admin

def fix_admin():
    username = 'admin'
    password = 'admin123'
    email = 'admin@example.com'
    
    # Create or update user
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': email,
            'is_staff': True,
            'is_superuser': True
        }
    )
    
    if not created:
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()
        print(f"✅ Updated existing user: {username}")
    else:
        user.set_password(password)
        user.save()
        print(f"✅ Created new user: {username}")
    
    # Create admin profile
    admin, created = Admin.objects.get_or_create(
        user=user,
        defaults={'department': 'Administration'}
    )
    
    if created:
        print(f"✅ Created admin profile for {username}")
    else:
        print(f"✅ Admin profile already exists for {username}")
    
    print(f"\nLogin with:")
    print(f"  Username: {username}")
    print(f"  Password: {password}")

if __name__ == "__main__":
    fix_admin()