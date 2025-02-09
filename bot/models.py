from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class status(models.Model):
    name = models.CharField(max_length=100)
    

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)  # Email as the unique identifier
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    lawyer_type = models.CharField(max_length=50, default='Criminal')

    USERNAME_FIELD = 'email'  # Set email as the default login field
    REQUIRED_FIELDS = ['username', 'phone_number']  # Fields required on superuser creation

    def __str__(self):
        return self.email