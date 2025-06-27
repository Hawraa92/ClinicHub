# accounts/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from accounts.models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User

    list_display = [
        'email', 
        'username', 
        'role', 
        'is_approved', 
        'is_staff', 
        'is_superuser', 
        'is_active'
    ]
    list_filter = [
        'role', 
        'is_approved', 
        'is_staff', 
        'is_superuser', 
        'is_active'
    ]
    search_fields = ['email', 'username']
    ordering = ['email']

    # Fields displayed when editing an existing user
    fieldsets = (
        (None, {
            "fields": ("email", "username", "password")
        }),
        (_("Role & Approval"), {
            "fields": ("role", "is_approved")
        }),
        (_("Permissions"), {
            "fields": (
                "is_staff",
                "is_active",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),
        (_("Important Dates"), {
            "fields": ("last_login", "date_joined")
        }),
    )

    # Fields displayed when creating a new user
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email",
                "username",
                "role",
                "is_approved",
                "password1",
                "password2",
                "is_staff",
                "is_active",
            ),
        }),
    )

    filter_horizontal = ("groups", "user_permissions",)
