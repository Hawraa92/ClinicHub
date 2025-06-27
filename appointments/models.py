# appointments/models.py

from django.db import models, transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from doctor.models import Doctor
from patient.models import Patient


class Appointment(models.Model):
    """
    Represents a booking of a patient with a doctor.
    Used for scheduling purposes only (no medical data).
    """

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        verbose_name="Patient",
        help_text="Select the patient from the registered list"
    )

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        verbose_name="Doctor",
        help_text="Doctor who will see the patient",
        db_index=True,
    )

    scheduled_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Scheduled Time",
        help_text="Date and time of the appointment",
        db_index=True,
    )

    queue_number = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name="Queue Number",
        help_text="Auto-generated based on the doctor's daily appointments"
    )

    iqd_amount = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        default=0,
        verbose_name="Amount (IQD)",
        help_text="Amount in Iraqi dinars"
    )

    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notes",
        help_text="Optional notes about the appointment"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Status",
        help_text="Current status of the appointment"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At",
        db_index=True,
    )

    class Meta:
        ordering = ['scheduled_time']
        verbose_name = "Appointment"
        verbose_name_plural = "Appointments"
        indexes = [
            models.Index(fields=['doctor', 'scheduled_time'], name='appt_doctor_sched_idx'),
            models.Index(fields=['scheduled_time'], name='appt_sched_idx'),
            models.Index(fields=['created_at'], name='appt_created_idx'),
        ]

    def clean(self):
        if self.scheduled_time:
            conflict = Appointment.objects.exclude(pk=self.pk).filter(
                doctor=self.doctor,
                scheduled_time=self.scheduled_time
            )
            if conflict.exists():
                raise ValidationError("This time slot is already booked for this doctor.")
        if self.iqd_amount is not None and self.iqd_amount < 0:
            raise ValidationError("IQD amount cannot be negative.")

    def save(self, *args, **kwargs):
        if not self.pk and self.scheduled_time:
            appointment_date = self.scheduled_time.date()
            with transaction.atomic():
                Doctor.objects.select_for_update().get(pk=self.doctor.pk)
                today_count = (
                    Appointment.objects
                    .select_for_update()
                    .filter(
                        doctor=self.doctor,
                        scheduled_time__date=appointment_date
                    )
                    .count()
                )
                self.queue_number = today_count + 1
        if self.iqd_amount is None:
            self.iqd_amount = 0
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        patient_name = getattr(self.patient, 'full_name', str(self.patient))
        doctor_name = getattr(self.doctor.user, 'get_full_name', lambda: str(self.doctor.user))()
        return f"{patient_name} → Dr. {doctor_name} (#{self.queue_number}) | {self.iqd_amount:,} IQD"


class PatientBookingRequest(models.Model):
    """
    Represents a booking request from a public patient (non-registered).
    Used in public-facing booking form.
    """
    full_name = models.CharField(max_length=100, verbose_name="Full Name")
    date_of_birth = models.DateField(verbose_name="Date of Birth")
    contact_info = models.CharField(max_length=200, verbose_name="Contact Information")

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        verbose_name="Requested Doctor",
        help_text="Doctor the patient wants to consult"
    )

    scheduled_time = models.DateTimeField(verbose_name="Requested Time")

    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name="Submitted At")

    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('rejected', 'Rejected')],
        default='pending',
        verbose_name="Status"
    )

    def __str__(self):
        return f"{self.full_name} → Dr. {self.doctor.user.get_full_name()} on {self.scheduled_time.strftime('%Y-%m-%d %I:%M %p')}"

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating:
            Notification.objects.create(
                title='New Patient Booking',
                message=f"{self.full_name} requested an appointment with Dr. {self.doctor.user.get_full_name()} on {self.scheduled_time:%Y-%m-%d %I:%M %p}.",
                related_booking_request=self
            )


class Notification(models.Model):
    """
    Notification for the secretary to review new public booking requests.
    """
    title = models.CharField(max_length=200, verbose_name="Title")
    message = models.TextField(verbose_name="Message")
    is_read = models.BooleanField(default=False, verbose_name="Read Status")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    # Link to the public booking request if applicable
    related_booking_request = models.ForeignKey(
        PatientBookingRequest,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='notifications',
        verbose_name="Related Booking Request"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"{self.title} - {'Read' if self.is_read else 'Unread'}"
