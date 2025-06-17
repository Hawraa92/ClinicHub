from django import forms
from .models import Doctor

class DoctorProfileForm(forms.ModelForm):
    """
    Form for doctors to view and update their profile, excluding non-editable fields.
    """
    class Meta:
        model = Doctor
        fields = ['full_name', 'specialty', 'phone', 'clinic_address']
        
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True,  # ✅ أفضل من 'readonly': 'readonly'
                'placeholder': 'Your full name'
            }),
            'specialty': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True,
                'placeholder': 'Your medical specialty'
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
        }

        labels = {
            'full_name': 'Doctor Name',
            'specialty': 'Specialization',
            'phone': 'Phone Number',
            'clinic_address': 'Clinic Address',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ✅ إضافة classes إضافية أو تخصيص لاحق هنا
        self.fields['phone'].required = False
        self.fields['clinic_address'].required = False
