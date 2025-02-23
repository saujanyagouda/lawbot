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

class Client(models.Model):
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    email_address = models.EmailField(unique=True)
    status = models.BooleanField(default=True)  # Example: Active or Inactive Client
    is_active = models.BooleanField(default=True)  # Whether the client is currently active

    def __str__(self):
        return self.name


class Task(models.Model):
    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
    ]

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
    ]

    task_name = models.CharField(max_length=255)
    related_to = models.CharField(max_length=255)
    case_number = models.CharField(max_length=50, unique=True)
    start_date = models.DateField()
    deadline = models.DateField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Medium')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Pending')

    def __str__(self):
        return f"{self.task_name} ({self.case_number})"


