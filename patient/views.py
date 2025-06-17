# patient/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import DoctorPatientForm, SecretaryPatientForm
from .models import Patient

# Temporary dummy prediction (until AI model is added)
def predict_diabetes(patient):
    return "Pending"

# 🔹 Get user role by group name
def get_user_role(user):
    return user.groups.first().name if user.groups.exists() else None

# 🔸 Create Patient View
@login_required
def create_patient(request):
    user_role = get_user_role(request.user)
    # إذا كان دور المستخدم "Doctors" استخدم نموذج الطبيب، وإلا استخدم نموذج السكرتيرة
    form_class = DoctorPatientForm if user_role == 'Doctors' else SecretaryPatientForm

    if request.method == 'POST':
        form = form_class(request.POST)
        if form.is_valid():
            patient = form.save(commit=False)
            # إذا كان المستخدم طبيبًا، حدِّث حقل التنبؤ بالسكري
            if user_role == 'Doctors':
                patient.diabetes_prediction = predict_diabetes(patient)
            patient.save()

            # 🔁 إعادة التوجيه بناءً على الدور
            if user_role == 'Doctors':
                return redirect('patients:list')  # إذا أنشأ الطبيب المريض، عد إلى قائمة المرضى للطبيب
            else:
                return redirect('appointments:secretary_dashboard')  # إذا أنشأت السكرتيرة المريض، عد إلى داشبورد السكرتيرة
    else:
        form = form_class()

    return render(request, 'patient/create_patient.html', {'form': form})


# 🔸 List of Patients (يمكن للطبيب رؤية جميع مرضاه هنا)
@login_required
def patient_list(request):
    patients = Patient.objects.all()
    return render(request, 'patient/patient_list.html', {'patients': patients})


# 🔸 Patient Details View
@login_required
def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    return render(request, 'patient/patient_detail.html', {'patient': patient})


# 🔸 Edit Patient View
@login_required
def edit_patient(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    user_role = get_user_role(request.user)
    form_class = DoctorPatientForm if user_role == 'Doctors' else SecretaryPatientForm

    if request.method == 'POST':
        form = form_class(request.POST, instance=patient)
        if form.is_valid():
            updated_patient = form.save(commit=False)
            if user_role == 'Doctors':
                updated_patient.diabetes_prediction = predict_diabetes(updated_patient)
            updated_patient.save()
            return redirect('patients:detail', pk=updated_patient.pk)
    else:
        form = form_class(instance=patient)

    return render(request, 'patient/edit_patient.html', {'form': form, 'patient': patient})


# 🔸 Patient Personal Dashboard (for logged-in patient)
@login_required
def patient_dashboard(request):
    try:
        patient = Patient.objects.get(email=request.user.email)
    except Patient.DoesNotExist:
        return render(request, 'patient/dashboard.html', {
            'patient': None,
            'error': 'No patient record found for your account.'
        })

    return render(request, 'patient/dashboard.html', {'patient': patient})
