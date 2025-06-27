# patient/forms.py

from django import forms
from django.contrib.auth import get_user_model
from .models import Patient
from doctor.models import Doctor  # ✅ أضفنا موديل الطبيب

User = get_user_model()

# === Doctor Form (Full Access) ===
class DoctorPatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            'full_name',
            'date_of_birth',
            'gender',
            'mobile',
            'email',
            'address',
            'past_medical_history',
            'drug_history',
            'investigations',
            'bmi',
            'hbA1c_level',
            'blood_glucose_level',
            'hypertension',
            'heart_disease',
            'smoking_history',
            'race',
            'clinical_notes',
            'doctor',
        ]
        widgets = {
            # نفس إعداداتك السابقة...
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mobile number'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Address'}),
            'past_medical_history': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'drug_history': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'investigations': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'bmi': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'hbA1c_level': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'blood_glucose_level': forms.NumberInput(attrs={'class': 'form-control'}),
            'hypertension': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'heart_disease': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'smoking_history': forms.Select(attrs={'class': 'form-select'}),
            'race': forms.Select(attrs={'class': 'form-select'}),
            'clinical_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'doctor': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['doctor'].queryset = Doctor.objects.all()
        self.fields['doctor'].label_from_instance = lambda obj: obj.full_name


# === Secretary Form (Limited Access) ===
class SecretaryPatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            'full_name',
            'date_of_birth',
            'address',
            'doctor',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Address'}),
            'doctor': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['doctor'].queryset = Doctor.objects.all()
        self.fields['doctor'].required = True
        self.fields['doctor'].label_from_instance = lambda obj: obj.full_name
