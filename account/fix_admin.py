# account/management/commands/fix_admin.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from account.models import Admin

class Command(BaseCommand):
    help = 'Fixes admin user creation and permissions'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default='admin', help='Admin username')
        parser.add_argument('--password', type=str, default='admin123', help='Admin password')
        parser.add_argument('--email', type=str, default='admin@example.com', help='Admin email')

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        email = options['email']
        
        self.stdout.write("=" * 50)
        self.stdout.write("FIXING ADMIN USER")
        self.stdout.write("=" * 50)
        
        # Check if user exists
        try:
            user = User.objects.get(username=username)
            self.stdout.write(f"✅ User '{username}' found")
            
            # Update password to ensure it's correct
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.save()
            self.stdout.write(f"✅ Password updated for '{username}'")
            
        except User.DoesNotExist:
            self.stdout.write(f"❌ User '{username}' not found. Creating...")
            # Create new user
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                is_staff=True,
                is_superuser=True
            )
            self.stdout.write(f"✅ User '{username}' created")
        
        # Check if admin profile exists
        try:
            admin = Admin.objects.get(user=user)
            self.stdout.write(f"✅ Admin profile already exists for '{username}'")
        except Admin.DoesNotExist:
            self.stdout.write(f"❌ No admin profile found. Creating...")
            admin = Admin.objects.create(
                user=user,
                department='Administration'
            )
            self.stdout.write(f"✅ Admin profile created for '{username}'")
        
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("ADMIN USER FIXED!")
        self.stdout.write(f"Username: {username}")
        self.stdout.write(f"Password: {password}")
        self.stdout.write("=" * 50)
        
        # List all users and their admin status
        self.stdout.write("\nAll Users:")
        for u in User.objects.all():
            try:
                is_admin = Admin.objects.filter(user=u).exists()
                admin_status = "✓ Admin" if is_admin else "✗ Not Admin"
            except:
                admin_status = "✗ Not Admin"
            
            self.stdout.write(f"  - {u.username}: Staff={u.is_staff}, Superuser={u.is_superuser}, {admin_status}")