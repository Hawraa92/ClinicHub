from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.template.defaultfilters import filesizeformat
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.urls import reverse

import uuid
import os
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

def archive_file_path(instance, filename):
    """
    Dynamic upload path: patient_archives/<archive_id>/<filename>
    """
    ext = filename.split('.')[-1]
    return f'patient_archives/{instance.archive.id}/{uuid.uuid4()}.{ext}'


def validate_file_size(value):
    """
    Ensure uploaded file is not larger than 10MB
    """
    limit_mb = 10
    if value.size > limit_mb * 1024 * 1024:
        raise ValidationError(f"Max file size is {limit_mb}MB.")


class PatientArchive(models.Model):
    ARCHIVE_TYPES = [
        ('visit', 'Visit'),
        ('lab', 'Lab Result'),
        ('scan', 'Scan'),
        ('prescription', 'Prescription'),
        ('other', 'Other'),
    ]

    patient = models.ForeignKey(
        'patient.Patient',
        on_delete=models.SET_NULL,
        null=True,
        related_name='medical_archives',
        help_text="Select the patient for this archive"
    )

    doctor = models.ForeignKey(
        'doctor.Doctor',
        on_delete=models.SET_NULL,
        null=True,
        related_name='medical_patient_archives',
        help_text="Doctor who created this archive"
    )

    title = models.CharField(
        max_length=255,
        help_text="e.g., Visit Note 1, Blood Test Result"
    )

    notes = models.TextField(
        blank=True,
        help_text="Doctor's notes or case description"
    )

    archive_type = models.CharField(
        max_length=50,
        choices=ARCHIVE_TYPES,
        default='visit',
        help_text="Type of archive: Visit, Lab Result, Scan, etc."
    )

    is_critical = models.BooleanField(
        default=False,
        help_text="Check if the archive contains critical or urgent information"
    )

    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Created At"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Last Updated"
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='medical_archives_created',
        help_text="User who created this archive entry"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Patient Archive"
        verbose_name_plural = "Patient Archives"

    def __str__(self):
        return f"{self.patient.full_name} - {self.title} ({self.get_archive_type_display()})"

    def get_color_tag(self):
        """
        Returns a Bootstrap color class based on archive type
        """
        color_map = {
            'visit': 'primary',
            'lab': 'success',
            'scan': 'warning',
            'prescription': 'info',
            'other': 'secondary',
        }
        return color_map.get(self.archive_type or 'other', 'secondary')

    def get_absolute_url(self):
        return reverse('medical_archive:archive_detail', args=[self.pk])

    def clean(self):
        """
        Ensure valid archive type and prevent duplicate entries
        """
        if self.archive_type not in dict(self.ARCHIVE_TYPES):
            raise ValidationError("Invalid archive type selected.")

        duplicate = PatientArchive.objects.filter(
            patient=self.patient,
            doctor=self.doctor,
            title=self.title
        ).exclude(pk=self.pk)

        if duplicate.exists():
            raise ValidationError("An archive with the same title already exists for this patient and doctor.")


class ArchiveAttachment(models.Model):
    archive = models.ForeignKey(
        PatientArchive,
        on_delete=models.CASCADE,
        related_name='attachments',
        help_text="Parent archive this file is attached to"
    )

    file = models.FileField(
        upload_to=archive_file_path,
        validators=[
            FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png', 'gif']),
            validate_file_size
        ],
        help_text="Upload PDF, image, or document related to the archive"
    )

    description = models.CharField(
        max_length=255,
        blank=True,
        help_text="e.g., Blood Test PDF, Chest Scan Image"
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Uploaded At"
    )

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = "Attachment"
        verbose_name_plural = "Attachments"

    def __str__(self):
        filename = os.path.basename(self.file.name)
        return f"{filename} - {self.description or 'No description'}"

    def is_image(self):
        """
        Returns True if the file is an image
        """
        return self.file.name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))

    def is_pdf(self):
        """
        Returns True if the file is a PDF
        """
        return self.file.name.lower().endswith('.pdf')

    def file_size(self):
        """
        Returns human-readable file size
        """
        return filesizeformat(self.file.size)


@receiver(post_delete, sender=ArchiveAttachment)
def delete_attachment_file(sender, instance, **kwargs):
    """
    Delete the actual file from storage when the model is deleted
    """
    if instance.file:
        instance.file.delete(save=False)
        try:
            folder = os.path.dirname(instance.file.path)
            if not os.listdir(folder):
                os.rmdir(folder)
        except Exception as e:
            logger.warning(f"Error removing empty archive folder: {e}")
