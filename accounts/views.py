# accounts/views.py

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import PatientSignUpForm, LoginForm

def register(request):
    """
    Public registration endpoint for patients only.
    """
    if request.method == 'POST':
        form = PatientSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "✅ Your patient account has been created and you are now logged in.")
            return redirect('patient:dashboard')
        else:
            messages.error(request, "❌ Please correct the errors below.")
    else:
        form = PatientSignUpForm()
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    """
    Authenticate and log in a user, redirecting by role.
    """
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Redirect based on role
            if user.role == 'patient':
                return redirect('patient:dashboard')
            elif user.role == 'doctor':
                return redirect('doctor:dashboard')
            elif user.role == 'secretary':
                return redirect('appointments:secretary_dashboard')
            else:
                messages.warning(request, "⚠ Unknown role—sending you home.")
                return redirect('home:index')
        else:
            messages.error(request, "❌ Invalid email or password.")
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    """
    Log out the current user and send them to login page.
    """
    logout(request)
    messages.info(request, "👋 You have been logged out.")
    return redirect('accounts:login')
