# File: prescription/models.py
# Replace the content of your existing prescription/models.py with the code below

from django.db import models
from django.urls import reverse
from django.conf import settings
from appointments.models import Appointment
from doctor.models import Doctor

import qrcode
from io import BytesIO
from django.core.files import File
import logging

logger = logging.getLogger(__name__)

class Prescription(models.Model):
    """
    Represents a doctor's prescription linked to an appointment, with auto-generated QR code and PDF.
    """
    appointment        = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        verbose_name="Appointment",
        help_text="Related appointment from which patient info is derived"
    )
    doctor             = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        verbose_name="Doctor",
        help_text="Doctor who issued this prescription"
    )

    # Denormalized patient info from appointment
    patient_full_name  = models.CharField(max_length=100, verbose_name="Patient Name")
    age                = models.PositiveIntegerField(verbose_name="Patient Age")

    # Prescription details
    instructions       = models.TextField(blank=True, null=True, verbose_name="Additional Instructions")
    voice_note         = models.FileField(
        upload_to='voice_notes/', blank=True, null=True,
        verbose_name="Doctor's Voice Note"
    )
    doctor_signature   = models.ImageField(
        upload_to='signatures/', blank=True, null=True,
        verbose_name="Doctor Signature"
    )
    doctor_logo        = models.ImageField(
        upload_to='logos/', blank=True, null=True,
        verbose_name="Clinic Logo"
    )
    pdf_file           = models.FileField(
        upload_to='prescriptions/', blank=True, null=True,
        verbose_name="Prescription PDF"
    )

    date_issued = models.DateTimeField(auto_now_add=True, verbose_name="Date Issued")

    qr_code    = models.ImageField(
        upload_to='qrcodes/', blank=True, null=True,
        verbose_name="QR Code"
    )

    class Meta:
        ordering = ['-date_issued']
        verbose_name = "Prescription"
        verbose_name_plural = "Prescriptions"

    def generate_qr_code(self):
        """
        Generate a QR Code containing basic prescription info and save to qr_code field.
        """
        try:
            site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
            url = f"{site_url}{self.get_absolute_url()}"
            data = (
                f"Prescription ID: {self.pk}\n"
                f"Patient: {self.patient_full_name}\n"
                f"Date: {self.date_issued.strftime('%Y-%m-%d %H:%M')}\n"
                f"View: {url}"
            )
            qr = qrcode.make(data)
            buffer = BytesIO()
            qr.save(buffer, format='PNG')
            buffer.seek(0)
            filename = f'qr_{self.pk}.png'
            self.qr_code.save(filename, File(buffer), save=False)
            buffer.close()
        except Exception as e:
            logger.error(f"QR code generation failed: {e}")

    def save(self, *args, **kwargs):
        """
        On save, copy patient info from appointment and generate QR code if this is a new record.
        """
        # Copy patient details
        if self.appointment:
            self.patient_full_name = self.appointment.patient.full_name
            self.age = self.appointment.patient.age

        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Generate QR code only once on creation
        if is_new and not self.qr_code:
            self.generate_qr_code()
            super().save(update_fields=['qr_code'])

    def get_absolute_url(self):
        return reverse('prescription:prescription_detail', kwargs={'pk': self.pk})

    def __str__(self):
        return f"Prescription #{self.pk} for {self.patient_full_name}"


class Medication(models.Model):
    """
    Medication entries linked to a Prescription.
    """
    prescription = models.ForeignKey(
        Prescription,
        related_name='medications',
        on_delete=models.CASCADE
    )
    name   = models.CharField(max_length=200, verbose_name="Medication Name")
    dosage = models.CharField(max_length=255, verbose_name="Dosage")

    def __str__(self):
        return f"{self.name} — {self.dosage}"
