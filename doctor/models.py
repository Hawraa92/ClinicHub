# doctor/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
import re

User = get_user_model()

# ✅ Validate phone number format
def validate_phone(value):
    if value and not re.match(r'^\+?[0-9]*$', value):
        raise ValidationError(f"{value} is not a valid phone number.")

class Doctor(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="doctor_profile"
    )

    full_name = models.CharField(
        max_length=255,
        verbose_name="Full Name"
    )

    specialty = models.CharField(
        max_length=100,
        verbose_name="Specialty"
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[validate_phone],
        verbose_name="Phone Number"
    )

    clinic_address = models.TextField(
        blank=True,
        verbose_name="Clinic Address"
    )

    photo = models.ImageField(
        upload_to="doctors/photos/",
        blank=True,
        null=True,
        verbose_name="Profile Photo"
    )

    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        blank=True,
        verbose_name="Gender"
    )

    short_bio = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Short Biography",
        help_text="A brief summary displayed on the doctor's profile card."
    )

    available = models.BooleanField(
        default=True,
        verbose_name="Available for Booking",
        help_text="Indicates whether this doctor is publicly available for appointments."
    )

    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=5.0,
        verbose_name="Rating",
        help_text="Average patient rating."
    )

    # ✅ سعر الجلسة
    consultation_fee = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="Consultation Fee (IQD)"
    )

    # ✅ سنوات الخبرة
    experience_years = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="Years of Experience",
        help_text="Number of years the doctor has practiced medicine."
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At"
    )

    class Meta:
        indexes = [
            models.Index(fields=['specialty']),
        ]
        verbose_name = "Doctor"
        verbose_name_plural = "Doctors"

    def __str__(self):
        return (
            self.full_name
            or self.user.get_full_name()
            or self.user.username
            or f"Doctor #{self.pk}"
        )
