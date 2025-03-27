from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

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
    
    def get_full_name(self):  # Use a properly named method
        return f"{self.username}".strip()

class Client(models.Model):
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    email_address = models.EmailField(unique=True)
    status = models.BooleanField(default=True)  # Example: Active or Inactive Client
    is_active = models.BooleanField(default=True)  # Whether the client is currently active
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="client",null=True)

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
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="task",null=True)

    def __str__(self):
        return f"{self.task_name} ({self.case_number})"

class Case(models.Model):
    STATUS_CHOICES = [
        ('on-trial', 'On-Trial'),
        ('closed', 'Closed'),
        ('pending', 'Pending'),
        ('dismissed', 'Dismissed'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="cases")
    case_number = models.CharField(max_length=50, unique=True)  # No: 542344
    case_type = models.CharField(max_length=100)  # Case: Murder

    court_name = models.CharField(max_length=255)  # Court: RTC - Branch 4
    court_number = models.CharField(max_length=50)  # No: 3123
    magistrate_name = models.CharField(max_length=255)  # Magistrate: Judge Marvin Tapuyo

    petitioner = models.CharField(max_length=255)  # Will Cc Smith
    respondent = models.CharField(max_length=255)  # Will Smith

    next_hearing_date = models.DateField()  # 07-20-2021
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='on-trial')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="case",null=True)

    def __str__(self):
        return f"{self.client_name} - {self.case_number}"


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('RESCHEDULED', 'Rescheduled'),
    ]
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='appointments')
    date = models.DateField()
    time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    topic = models.TextField(blank=True, null=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="appointment",null=True)
    
    class Meta:
        ordering = ['date', 'time']
        
    def __str__(self):
        return f"{self.client.name} - {self.date} {self.time}"
    
    def is_past_due(self):
        appointment_datetime = timezone.make_aware(
            timezone.datetime.combine(self.date, self.time)
        )
        return appointment_datetime < timezone.now()


class Invoice(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PARTIAL', 'Partially Paid'),
        ('PAID', 'Fully Paid'),
    ]
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=20, unique=True)  # Will store as INV-XXXXX
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    due_amount = models.DecimalField(max_digits=10, decimal_places=2)
    service = models.CharField(max_length=255)
    payment_mode = models.CharField(max_length=255)  
    due_date = models.DateTimeField()
    
    
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    payment_status = models.CharField(
        max_length=10, 
        choices=PAYMENT_STATUS_CHOICES, 
        default='PENDING'
    )
    
    invoice_file = models.FileField(upload_to='invoices/', blank=True, null=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="invoice",null=True)
    
    def __str__(self):
        return f"{self.invoice_number} - {self.client.name}"
    
    def save(self, *args, **kwargs):
        # Calculate due amount automatically
        self.due_amount = self.total_amount - self.paid_amount
        
        # Set payment status based on amount paid
        if self.paid_amount == 0:
            self.payment_status = 'PENDING'
        elif self.paid_amount < self.total_amount:
            self.payment_status = 'PARTIAL'
        else:
            self.payment_status = 'PAID'
            
        # Generate invoice number if not provided
        if not self.invoice_number:
            last_invoice = Invoice.objects.all().order_by('-id').first()
            if last_invoice:
                last_id = int(last_invoice.invoice_number.split('-')[1])
                self.invoice_number = f"INV-{last_id + 1:05d}"
            else:
                self.invoice_number = "INV-00001"
                
        super().save(*args, **kwargs)

class ChatMessage(models.Model):
    session_id = models.CharField(max_length=100, db_index=True)
    role = models.CharField(max_length=20)  # 'human', 'ai', 'system'
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        
