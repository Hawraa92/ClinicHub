# appointments/admin.py

from django.contrib import admin
from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = [
        'get_patient_name',
        'get_patient_age',
        'doctor',
        'scheduled_time',
        'queue_number',
        'iqd_amount',
        'status',
    ]

    list_filter = ['doctor', 'status']
    search_fields = ['patient__full_name', 'doctor__user__first_name', 'doctor__user__last_name']
    list_select_related = ('patient', 'doctor', 'doctor__user')
    date_hierarchy = 'scheduled_time'
    ordering = ['-scheduled_time']

    @admin.display(description='Patient Name')
    def get_patient_name(self, obj):
        return obj.patient.full_name if obj.patient else '—'

    @admin.display(description='Patient Age')
    def get_patient_age(self, obj):
        return obj.patient.age if obj.patient and obj.patient.age is not None else '—'
