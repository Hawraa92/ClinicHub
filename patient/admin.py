# patient/admin.py

from django.contrib import admin
from .models import Patient

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = [
        'full_name',
        'mobile',
        'email',
        'gender',
        'doctor',               # Assigned doctor
        'diabetes_prediction'
    ]
    search_fields = [
        'full_name',
        'mobile',
        'email'
    ]
    list_filter = [
        'gender',
        'hypertension',
        'heart_disease',
        'smoking_history',
        'race',
        'doctor'               # Filter by assigned doctor
    ]
    readonly_fields = [
        'diabetes_prediction'  # AI-generated field should not be editable
    ]
    list_select_related = ('doctor',)  # Optimize joins when displaying doctor

    @admin.display(description='Age')
    def age(self, obj):
        """
        Display computed age from date_of_birth, if available.
        """
        return obj.age or '—'
