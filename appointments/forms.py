# appointments/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from .models import Appointment, PatientBookingRequest
from patient.models import Patient
from doctor.models import Doctor


class AppointmentForm(forms.ModelForm):
    """
    Form for booking an appointment using a pre-registered patient.
    Includes validation to prevent past or too-close appointments.
    """
    scheduled_time = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={
                'type': 'datetime-local',
                'class': 'form-control',
            }
        ),
        label='Appointment Time',
        help_text='Pick the appointment time using the calendar'
    )

    status = forms.ChoiceField(
        choices=Appointment.STATUS_CHOICES,
        widget=forms.Select(
            attrs={'class': 'form-select'}
        ),
        label='Status'
    )

    iqd_amount = forms.DecimalField(
        max_digits=15,
        decimal_places=0,
        min_value=0,
        required=False,
        widget=forms.NumberInput(
            attrs={'class': 'form-control', 'placeholder': 'Amount in IQD'}
        ),
        label='Amount (IQD)'
    )

    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional notes'}
        ),
        label='Notes'
    )

    class Meta:
        model = Appointment
        fields = ['patient', 'doctor', 'scheduled_time', 'status', 'iqd_amount', 'notes']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'doctor': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['patient'].queryset = Patient.objects.order_by('full_name')
        self.fields['doctor'].queryset = Doctor.objects.select_related('user').order_by('user__first_name')
        self.fields['doctor'].label_from_instance = lambda obj: obj.full_name

    def clean_scheduled_time(self):
        scheduled_time = self.cleaned_data.get('scheduled_time')
        if scheduled_time and scheduled_time < timezone.localtime():
            raise ValidationError("The selected time is in the past. Please choose a future time.")
        return scheduled_time

    def clean(self):
        cleaned_data = super().clean()
        doctor = cleaned_data.get('doctor')
        scheduled_time = cleaned_data.get('scheduled_time')
        if doctor and scheduled_time:
            window_start = scheduled_time - timedelta(minutes=1)
            window_end = scheduled_time + timedelta(minutes=1)
            overlapping = Appointment.objects.filter(
                doctor=doctor, scheduled_time__range=(window_start, window_end)
            ).exclude(pk=self.instance.pk)
            if overlapping.exists():
                raise ValidationError(
                    "You must leave at least one minute between appointments for this doctor."
                )
        cleaned_data['iqd_amount'] = cleaned_data.get('iqd_amount') or 0
        return cleaned_data


class PatientBookingForm(forms.ModelForm):
    """
    Public booking form for patients who may not be registered.
    Includes full_name, date_of_birth, phone number, doctor, and scheduled_time.
    """
    full_name = forms.CharField(
        max_length=100,
        label='Your Full Name',
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Enter your full name'}
        )
    )

    contact_info = forms.CharField(
        max_length=50,
        label='Your Phone Number',
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Your phone number'}
        )
    )

    date_of_birth = forms.DateField(
        label='Your Date of Birth',
        widget=forms.DateInput(
            attrs={'class': 'form-control', 'type': 'date'}
        )
    )

    scheduled_time = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local', 'class': 'form-control'}
        ),
        label='Preferred Time'
    )

    class Meta:
        model = PatientBookingRequest
        fields = ['full_name', 'date_of_birth', 'contact_info', 'doctor', 'scheduled_time']
        widgets = {
            'doctor': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['doctor'].queryset = Doctor.objects.all().order_by('user__first_name')
        self.fields['doctor'].label_from_instance = lambda obj: obj.full_name

    def clean_scheduled_time(self):
        scheduled_time = self.cleaned_data.get('scheduled_time')
        if scheduled_time and scheduled_time < timezone.now():
            raise ValidationError("Please choose a future time.")
        return scheduled_time
