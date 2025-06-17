# accounts/views.py

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db import transaction
from accounts.forms import RegisterForm, LoginForm
from doctor.models import Doctor


@transaction.atomic
def register_view(request):
    """
    Register a new user (doctor, secretary, or patient).
    If the user chooses the role 'doctor', create a corresponding Doctor record.
    """
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            # Save the User instance (sets password internally in RegisterForm.save())
            user = form.save()

            # If the new user is a doctor, create a Doctor record
            if user.role == 'doctor':
                Doctor.objects.create(
                    user=user,
                    full_name=user.username,    # أو user.get_full_name() إذا كنت تستخدمين حقول الاسم الكاملة
                    specialty='',
                    phone='',
                    clinic_address=''
                )

            messages.success(request, "✅ Account created successfully. Please log in.")
            return redirect('accounts:login')
        else:
            messages.error(request, "❌ Please correct the errors below.")
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """
    Authenticate and log in a user. Redirects to the correct dashboard based on user role.
    """
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # Role-based redirection
            if user.role == 'doctor':
                return redirect('doctor:dashboard')
            elif user.role == 'secretary':
                return redirect('appointments:secretary_dashboard')
            elif user.role == 'patient':
                return redirect('patients:dashboard')
            else:
                messages.warning(request, "⚠ Unknown user role. Redirected to homepage.")
                return redirect('home:index')
        else:
            messages.error(request, "❌ Invalid login credentials.")
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """
    Log out the current user and redirect to login page.
    """
    logout(request)
    messages.info(request, "👋 You have been logged out.")
    return redirect('accounts:login')
