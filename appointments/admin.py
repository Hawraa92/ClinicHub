from django.contrib import admin
from .models import Appointment, PatientBookingRequest, Notification


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
    search_fields = [
        'patient__full_name',
        'doctor__user__first_name',
        'doctor__user__last_name'
    ]
    list_select_related = ('patient', 'doctor', 'doctor__user')
    date_hierarchy = 'scheduled_time'
    ordering = ['-scheduled_time']

    @admin.display(description='Patient Name')
    def get_patient_name(self, obj):
        return obj.patient.full_name if obj.patient else '—'

    @admin.display(description='Patient Age')
    def get_patient_age(self, obj):
        # assumes Patient model has an .age property or field
        return obj.patient.age if obj.patient and getattr(obj.patient, 'age', None) is not None else '—'


@admin.register(PatientBookingRequest)
class PatientBookingRequestAdmin(admin.ModelAdmin):
    list_display = [
        'full_name',
        'doctor',
        'scheduled_time',
        'status',
        'submitted_at',
    ]
    list_filter = ['status', 'doctor']
    search_fields = [
        'full_name',
        'contact_info',
        'doctor__user__first_name',
        'doctor__user__last_name',
    ]
    list_select_related = ('doctor', 'doctor__user')
    date_hierarchy = 'submitted_at'
    ordering = ['-submitted_at']
    readonly_fields = ('submitted_at',)
    actions = ['mark_as_confirmed', 'mark_as_rejected']

    @admin.action(description='Mark selected booking requests as confirmed')
    def mark_as_confirmed(self, request, queryset):
        updated = queryset.update(status='confirmed')
        self.message_user(request, f"{updated} booking request(s) marked as confirmed.")

    @admin.action(description='Mark selected booking requests as rejected')
    def mark_as_rejected(self, request, queryset):
        updated = queryset.update(status='rejected')
        self.message_user(request, f"{updated} booking request(s) marked as rejected.")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'related_booking_request', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['title', 'message']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
