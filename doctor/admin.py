# doctor/admin.py
from django.contrib import admin
from .models import Doctor

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = [
        'full_name',
        'specialty',
        'consultation_fee',
        'experience_years',  # ✅ أضفنا سنوات الخبرة
        'phone',
        'available',
        'rating',
        'user',
    ]

    list_filter = [
        'available',
        'specialty',
        'gender',
        'rating',
    ]

    search_fields = [
        'full_name',
        'specialty',
        'phone',
        'user__email',
        'user__username',
    ]

    ordering = ['full_name']

    readonly_fields = [
        'created_at',
        'updated_at',
    ]

    fieldsets = (
        ('User Information', {
            'fields': (
                'user',
                'full_name',
                'gender',
                'specialty',
                'phone',
                'clinic_address',
                'photo',
            ),
        }),
        ('Professional Details', {
            'fields': (
                'short_bio',
                'available',
                'rating',
                'consultation_fee',
                'experience_years',  # ✅ أضفنا سنوات الخبرة هنا
            ),
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )
