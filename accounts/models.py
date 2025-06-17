# accounts/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=100, null=True, blank=True)

    ROLE_CHOICES = (
        ('doctor', 'Doctor'),
        ('secretary', 'Secretary'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='secretary')

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.username or self.email

    def save(self, *args, **kwargs):
        # إذا لم يُحدد username، نأخذ الجزء الذي يسبق @ من البريد
        if self.email and not self.username:
            email_username, _ = self.email.split("@")
            self.username = email_username
        super().save(*args, **kwargs)
