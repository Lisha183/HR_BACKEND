from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.db import models
from cloudinary.models import CloudinaryField
from django.conf import settings



class CustomUser(AbstractUser):
    is_hr = models.BooleanField(default=False)
    is_employee = models.BooleanField(default=True)

    def __str__(self):
        return self.username
    
class TestUpload(models.Model):
    title = models.CharField(max_length=100)
    image = CloudinaryField('image') 

    def __str__(self):
        return self.title
    
class EmployeeProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    department = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)


