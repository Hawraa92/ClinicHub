# accounts/urls.py

from django.urls import path
from django.contrib.auth import views as auth_views
from .views import register, login_view, logout_view

app_name = 'accounts'

urlpatterns = [
    # Patient self-registration
    path('register/', register, name='register'),

    # Login using custom login_view (redirects by role)
    path('login/', login_view, name='login'),

    # Logout using custom logout_view
    path('logout/', logout_view, name='logout'),

    # Password reset request
    path(
        'password_reset/',
        auth_views.PasswordResetView.as_view(
            template_name='registration/password_reset_form.html',
            email_template_name='registration/password_reset_email.html',
            subject_template_name='registration/password_reset_subject.txt',
            success_url='done/'
        ),
        name='password_reset'
    ),

    # Password reset link sent
    path(
        'password_reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='registration/password_reset_done.html'
        ),
        name='password_reset_done'
    ),

    # Password reset confirm (via email link)
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html',
            success_url='/accounts/reset/done/'
        ),
        name='password_reset_confirm'
    ),

    # Password reset complete
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='registration/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),
]
