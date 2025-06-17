from django.contrib import admin
from .models import Doctor

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'specialty', 'phone', 'user']
    list_filter = ['specialty']
    search_fields = ['full_name', 'specialty', 'phone', 'user__email']
    ordering = ['full_name']
    readonly_fields = ['created_at', 'updated_at']  

    fieldsets = (
        (None, {
            'fields': ('user', 'full_name', 'specialty', 'phone', 'clinic_address')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
