from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from .forms import DoctorPatientForm, SecretaryPatientForm
from .models import Patient

def predict_diabetes(patient):
    """
    Temporary dummy prediction until the AI model is integrated.
    """
    # Add actual prediction logic here later
    return "Pending"

def is_doctor(user):
    return user.groups.filter(name='Doctors').exists()

def is_secretary(user):
    return user.groups.filter(name='Secretaries').exists()

def is_patient(user):
    return hasattr(user, 'patient')

@login_required
def create_patient(request):
    user = request.user
    if not (is_doctor(user) or is_secretary(user)):
        raise PermissionDenied

    form_class = DoctorPatientForm if is_doctor(user) else SecretaryPatientForm

    if request.method == 'POST':
        form = form_class(request.POST, request.FILES)
        if form.is_valid():
            patient = form.save(commit=False)
            if is_doctor(user):
                patient.diabetes_prediction = predict_diabetes(patient)
            patient.save()
            return redirect('patient:list') if is_doctor(user) else redirect('appointments:secretary_dashboard')
    else:
        form = form_class()

    return render(request, 'patient/create_patient.html', {'form': form})

@login_required
def patient_list(request):
    user = request.user
    if not is_doctor(user):
        raise PermissionDenied

    # Filter parameters
    statuses = request.GET.getlist('status')
    genders = request.GET.getlist('gender')
    search_query = request.GET.get('q', '')
    sort = request.GET.get('sort', 'recent')
    
    patients_qs = Patient.objects.all()
    
    # Apply filters
    if search_query:
        patients_qs = patients_qs.filter(
            Q(full_name__icontains=search_query) |
            Q(mobile__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    if statuses:
        patients_qs = patients_qs.filter(diabetes_prediction__in=statuses)
    
    if genders:
        patients_qs = patients_qs.filter(gender__in=genders)
    
    # Apply sorting
    if sort == 'name_asc':
        patients_qs = patients_qs.order_by('full_name')
    elif sort == 'name_desc':
        patients_qs = patients_qs.order_by('-full_name')
    elif sort == 'status':
        patients_qs = patients_qs.order_by('diabetes_prediction')
    else:  # Default: recently added first
        patients_qs = patients_qs.order_by('-created_at')
    
    # Summary counts
    positive_count = patients_qs.filter(diabetes_prediction='Positive').count()
    one_week_ago = timezone.now() - timedelta(days=7)
    new_this_week = patients_qs.filter(created_at__gte=one_week_ago).count()
    
    # Pagination
    paginator = Paginator(patients_qs, 25)
    page_number = request.GET.get('page')
    patients = paginator.get_page(page_number)
    
    context = {
        'patients': patients,
        'positive_count': positive_count,
        'new_this_week': new_this_week,
        'search_query': search_query,
        'selected_statuses': statuses,
        'selected_genders': genders,
        'selected_sort': sort,
    }
    
    return render(request, 'patient/patient_list.html', context)

@login_required
def patient_detail(request, pk):
    user = request.user
    if not is_doctor(user):
        raise PermissionDenied

    patient = get_object_or_404(Patient, pk=pk)
    
    # Dummy confidence values for UI demonstration
    confidence = 85  # Replace with actual confidence value later
    confidence_angle = (confidence * 180) / 100  # Convert to gauge angle
    
    return render(request, 'patient/patient_detail.html', {
        'patient': patient,
        'confidence': confidence,
        'confidence_angle': confidence_angle
    })

@login_required
def edit_patient(request, pk):
    user = request.user
    if not is_doctor(user):
        raise PermissionDenied

    patient = get_object_or_404(Patient, pk=pk)

    if request.method == 'POST':
        form = DoctorPatientForm(request.POST, request.FILES, instance=patient)
        if form.is_valid():
            updated_patient = form.save(commit=False)
            updated_patient.diabetes_prediction = predict_diabetes(updated_patient)
            updated_patient.save()
            return redirect('patient:detail', pk=updated_patient.pk)
    else:
        form = DoctorPatientForm(instance=patient)

    return render(request, 'patient/edit_patient.html', {'form': form, 'patient': patient})

@login_required
def patient_dashboard(request):
    user = request.user
    if not is_patient(user):
        raise PermissionDenied

    try:
        patient = user.patient
    except Patient.DoesNotExist:
        return render(request, 'patient/dashboard.html', {
            'patient': None,
            'error': 'No patient record found for your account.'
        })

    return render(request, 'patient/dashboard.html', {'patient': patient})