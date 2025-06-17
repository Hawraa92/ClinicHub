# appointments/forms.py

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from .models import Appointment
from patient.models import Patient
from doctor.models import Doctor


class AppointmentForm(forms.ModelForm):
    """
    Form for booking an appointment using a pre-registered patient.
    Includes validation to prevent past or too‐close appointments.
    """

    scheduled_time = forms.DateTimeField(
        input_formats=["%Y-%m-%d %I:%M %p"],
        widget=forms.DateTimeInput(
            attrs={
                'class': 'form-control datetimepicker',
                'placeholder': 'YYYY-MM-DD hh:mm AM/PM',
                'data-enable-time': 'true',
                'data-date-format': 'Y-m-d h:i K',
            }
        ),
        label='Appointment Time',
        help_text='Use format: YYYY-MM-DD HH:MM AM/PM'
    )

    status = forms.ChoiceField(
        choices=Appointment.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Status'
    )

    usd_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Amount in USD'
        }),
        label='Amount (USD)'
    )

    iqd_amount = forms.DecimalField(
        max_digits=15,
        decimal_places=0,
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Amount in IQD'
        }),
        label='Amount (IQD)'
    )

    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Optional notes'
        }),
        label='Notes'
    )

    class Meta:
        model = Appointment
        fields = [
            'patient',
            'doctor',
            'scheduled_time',
            'status',
            'usd_amount',
            'iqd_amount',
            'notes'
        ]
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'doctor': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['patient'].queryset = (
            Patient.objects.only('id', 'full_name')
            .order_by('full_name')
        )
        self.fields['doctor'].queryset = (
            Doctor.objects.select_related('user')
            .only('id', 'user__first_name', 'user__last_name')
            .order_by('user__first_name')
        )

    def clean_scheduled_time(self):
        scheduled_time = self.cleaned_data.get('scheduled_time')
        if scheduled_time:
            now = timezone.localtime(timezone.now())
            if scheduled_time < now:
                raise ValidationError("The selected time is in the past. Please choose a future time.")
        return scheduled_time

    def clean(self):
        cleaned_data = super().clean()
        doctor = cleaned_data.get('doctor')
        scheduled_time = cleaned_data.get('scheduled_time')

        if doctor and scheduled_time:
            window_start = scheduled_time - timedelta(minutes=1)
            window_end = scheduled_time + timedelta(minutes=1)
            overlapping = (
                Appointment.objects
                .filter(doctor=doctor, scheduled_time__range=(window_start, window_end))
            )
            if self.instance.pk:
                overlapping = overlapping.exclude(pk=self.instance.pk)

            if overlapping.exists():
                raise ValidationError("You must leave at least one minute between appointments for this doctor.")

        # Handle empty values safely by setting to zero if not provided
        usd = cleaned_data.get('usd_amount')
        iqd = cleaned_data.get('iqd_amount')

        cleaned_data['usd_amount'] = usd if usd is not None else 0.00
        cleaned_data['iqd_amount'] = iqd if iqd is not None else 0

        if usd is not None and usd < 0:
            self.add_error('usd_amount', "USD amount cannot be negative.")
        if iqd is not None and iqd < 0:
            self.add_error('iqd_amount', "IQD amount cannot be negative.")

        return cleaned_data
