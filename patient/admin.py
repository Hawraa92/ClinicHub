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
        'doctor',               # إضافة عمود "الطبيب المعالج"
        'diabetes_prediction'
    ]
    search_fields = ['full_name', 'mobile', 'email']
    list_filter = [
        'gender',
        'hypertension',
        'heart_disease',
        'smoking_history',
        'race',
        'doctor'               # فلترة حسب الطبيب أيضاً
    ]
    readonly_fields = ['diabetes_prediction']
