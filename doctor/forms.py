from django import forms
from .models import Doctor

class DoctorProfileForm(forms.ModelForm):
    """
    Form for doctors to view and update their profile details.
    Certain fields are read-only.
    """
    class Meta:
        model = Doctor
        fields = [
            'full_name',
            'specialty',
            'gender',
            'phone',
            'clinic_address',
            'photo',
            'short_bio',
            'available',
            'consultation_fee',
        ]

        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True,
                'placeholder': 'Your full name'
            }),
            'specialty': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True,
                'placeholder': 'Your medical specialty'
            }),
            'gender': forms.Select(attrs={
                'class': 'form-control'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+964xxxxxxxxxx'
            }),
            'clinic_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter your clinic address here'
            }),
            'photo': forms.ClearableFileInput(attrs={
                'class': 'form-control-file'
            }),
            'short_bio': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Short description about you'
            }),
            'available': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'consultation_fee': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Consultation fee (IQD)'
            }),
        }

        labels = {
            'full_name': 'Doctor Name',
            'specialty': 'Specialization',
            'gender': 'Gender',
            'phone': 'Phone Number',
            'clinic_address': 'Clinic Address',
            'photo': 'Profile Photo',
            'short_bio': 'Short Bio',
            'available': 'Available for Booking',
            'consultation_fee': 'Consultation Fee',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Optional: customize required fields
        self.fields['phone'].required = False
        self.fields['clinic_address'].required = False
        self.fields['photo'].required = False
        self.fields['short_bio'].required = False
        self.fields['consultation_fee'].required = False
