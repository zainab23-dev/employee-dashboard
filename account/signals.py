from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Admin

@receiver(post_save, sender=User)
def create_admin_for_superuser(sender, instance, created, **kwargs):
    if instance.is_superuser or instance.is_staff:
        Admin.objects.get_or_create(
            user=instance,
            defaults={'department': 'Administration'}
        )