# doctor/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.utils.timezone import now
from django.views.decorators.http import require_GET
from datetime import timedelta
import json

from .models import Doctor
from medical_archive.models import PatientArchive
from prescription.models import Prescription
from patient.models import Patient
from appointments.models import Appointment

User = get_user_model()

@login_required
def dashboard_view(request):
    """
    Render the doctor's dashboard showing recent archives, prescriptions,
    statistics, and key metrics.
    """
    user = request.user

    try:
        doctor = Doctor.objects.get(user=user)
    except Doctor.DoesNotExist:
        return redirect('home:index')

    today = now().date()

    # Recent archives (limit to 5)
    archives = PatientArchive.objects.filter(doctor=doctor).order_by('-created_at')[:5]

    # Stats
    archive_count = PatientArchive.objects.filter(doctor=doctor).count()
    prescription_count = Prescription.objects.filter(doctor=doctor).count()
    patient_count = Patient.objects.filter(appointment__doctor=doctor).distinct().count()
    patients_today = Patient.objects.filter(
        appointment__doctor=doctor,
        appointment__scheduled_time__date=today
    ).distinct().count()
    appointments_today = Appointment.objects.filter(
        doctor=doctor,
        scheduled_time__date=today
    ).count()
    new_patients_today = Patient.objects.filter(created_at__date=today).count()

    # Weekly chart data (past 7 days)
    chart_labels = []
    chart_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = Appointment.objects.filter(
            doctor=doctor,
            scheduled_time__date=day
        ).count()
        chart_labels.append(day.strftime('%a'))  # e.g., Mon, Tue
        chart_data.append(count)

    chart_data_json = json.dumps({
        'labels': chart_labels,
        'data': chart_data
    })

    # Today's appointments
    today_appointments = Appointment.objects.filter(
        doctor=doctor,
        scheduled_time__date=today
    )

    context = {
        'doctor': doctor,
        'archives': archives,
        'archive_count': archive_count,
        'prescription_count': prescription_count,
        'patient_count': patient_count,
        'stats': {
            'patients_today': patients_today,
            'appointments_today': appointments_today,
            'new_patients_today': new_patients_today,
        },
        'chart_data_json': chart_data_json,
        'today_appointments': today_appointments,
    }

    return render(request, 'doctor/doctor_dashboard.html', context)


@login_required
def doctor_dashboard(request):
    """
    Display the list of all patients related to the logged-in doctor.
    """
    if getattr(request.user, 'role', None) != 'doctor':
        raise PermissionDenied("Access restricted to doctors only.")

    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        return redirect('home:index')

    patients = Patient.objects.filter(appointment__doctor=doctor).order_by('full_name')

    return render(request, 'doctor/patient_records.html', {
        'patients': patients,
        'doctor': doctor,
    })


@require_GET
def available_doctors_list(request):
    """
    Public view to display all doctors who are currently available for booking.
    """
    doctors = Doctor.objects.filter(available=True).order_by('full_name')
    return render(request, 'doctor/available_doctors.html', {
        'doctors': doctors
    })
