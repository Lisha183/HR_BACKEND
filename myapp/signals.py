from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import EmployeeProfile, CustomUser

@receiver(post_save, sender=CustomUser)
def create_employee_profile(sender, instance, created, **kwargs):
    if created and instance.is_employee:
        EmployeeProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=CustomUser)
def save_employee_profile(sender, instance, **kwargs):
    if instance.is_employee:
        try:
            instance.profile.save()
        except EmployeeProfile.DoesNotExist:
            pass

