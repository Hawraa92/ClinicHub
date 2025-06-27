# accounts/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    # Use email as the unique identifier
    email = models.EmailField(unique=True)

    # We’ll auto-fill username from email if left blank
    username = models.CharField(max_length=100, null=True, blank=True)

    ROLE_CHOICES = (
        ('doctor',    'Doctor'),
        ('secretary', 'Secretary'),
        ('patient',   'Patient'),
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='patient',
        help_text="Determines which interface the user can access"
    )

    is_approved = models.BooleanField(
        default=False,
        help_text="Must be approved by admin before logging in (for doctor/secretary)"
    )

    # Tell Django to use email as the login field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.get_full_name() or self.email

    def save(self, *args, **kwargs):
        # If username blank, populate it from email local‐part
        if self.email and not self.username:
            self.username = self.email.split('@')[0]
        super().save(*args, **kwargs)
