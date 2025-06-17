from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
import re

User = get_user_model()

# ✅ تحقق من صحة رقم الهاتف
def validate_phone(value):
    if value and not re.match(r'^\+?[0-9]*$', value):
        raise ValidationError(f"{value} ليس رقم هاتف صالح.")

class Doctor(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="doctor_profile"
    )
    
    # ✅ الاسم الكامل كما يُراد ظهوره في الوصفات والمواعيد
    full_name = models.CharField(max_length=255, verbose_name="Full Name")

    specialty = models.CharField(max_length=100, verbose_name="Specialty")

    phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[validate_phone],
        verbose_name="Phone Number"
    )

    clinic_address = models.TextField(
        blank=True, verbose_name="Clinic Address"
    )

    photo = models.ImageField(
        upload_to="doctors/photos/",
        blank=True,
        null=True,
        verbose_name="Profile Photo"
    )

    # ✅ آمنة تمامًا ولا تسبب أي مشاكل
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['specialty']),
        ]
        verbose_name = "Doctor"
        verbose_name_plural = "Doctors"

    def __str__(self):
        return self.full_name or self.user.get_full_name() or self.user.username or f"Doctor #{self.pk}"
