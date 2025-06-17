# File: prescription/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.utils import timezone
from urllib.parse import quote
from xhtml2pdf import pisa
import io
import os
import logging

from django.conf import settings
from .forms import PrescriptionForm, MedicationFormSet
from .models import Prescription
from appointments.models import Appointment
from medical_archive.models import PatientArchive
from doctor.models import Doctor

logger = logging.getLogger(__name__)


@login_required
def doctor_dashboard(request):
    """
    Display the doctor's dashboard with counts of prescriptions, patients, and archives.
    (If you need this view, add its URL in prescription/urls.py)
    """
    doctor = get_object_or_404(Doctor, user=request.user)

    prescriptions_count = Prescription.objects.filter(doctor=doctor).count()
    patients_count = (
        Appointment.objects
        .filter(doctor=doctor)
        .values('patient')
        .distinct()
        .count()
    )
    archives_count = PatientArchive.objects.filter(doctor=doctor).count()

    return render(request, 'prescription/doctor_dashboard.html', {
        'prescriptions_count': prescriptions_count,
        'patients_count': patients_count,
        'archives_count': archives_count,
    })


@login_required
def new_prescription(request):
    """
    Redirect to the next appointment today without a prescription,
    then forward to create_prescription with its ID.
    """
    doctor = get_object_or_404(Doctor, user=request.user)
    today = timezone.localdate()

    next_appointment = (
        Appointment.objects
        .filter(doctor=doctor, scheduled_time__date=today)
        .exclude(prescription__isnull=False)
        .order_by('scheduled_time')
        .first()
    )
    if next_appointment:
        return redirect('prescription:create', appointment_id=next_appointment.pk)

    messages.info(request, "No new appointments for today.")
    return redirect('prescription:list')


@login_required
def prescription_list(request):
    """
    Display a searchable, chronological list of prescriptions.
    """
    prescriptions = Prescription.objects.order_by('-date_issued')
    search_query = request.GET.get('q', '')
    if search_query:
        prescriptions = prescriptions.filter(patient_full_name__icontains=search_query)

    doctors = Doctor.objects.all()

    return render(request, 'prescription/prescription_list.html', {
        'prescriptions': prescriptions,
        'search_query': search_query,
        'doctors': doctors,
    })


@login_required
def create_prescription(request, appointment_id):
    """
    Handle creation of a new prescription:
      1) Save prescription data
      2) Save medication formset
      3) Optionally archive it
      4) Generate and store a PDF
      5) Redirect to next appointment or back to list
    """
    appointment = get_object_or_404(Appointment, pk=appointment_id)

    if request.method == 'POST':
        form = PrescriptionForm(request.POST, request.FILES, appointment_id=appointment.id)
        med_formset = MedicationFormSet(request.POST, request.FILES, instance=None)

        if form.is_valid():
            # 1) Save prescription
            prescription = form.save(commit=False)
            prescription.appointment = appointment
            prescription.doctor = appointment.doctor
            prescription.patient_full_name = appointment.patient.full_name
            prescription.age = appointment.patient.age
            prescription.save()

            # 2) Save medications
            med_formset.instance = prescription
            if med_formset.is_valid():
                med_formset.save()
            else:
                logger.warning("MedicationFormSet invalid: %s", med_formset.errors)

            # 3) Optional archiving
            if form.cleaned_data.get('archive_prescription'):
                try:
                    PatientArchive.objects.create(
                        doctor=prescription.doctor,
                        title=f"Prescription for {prescription.patient_full_name}",
                        notes=prescription.instructions or '',
                        archive_type='prescription',
                        created_by=request.user
                    )
                except Exception as e:
                    logger.error("Failed to archive prescription %s: %s", prescription.pk, e)

            # 4) Generate PDF
            buffer = io.BytesIO()
            try:
                html = render_to_string('prescription/pdf_template.html', {'prescription': prescription})
                pisa_status = pisa.CreatePDF(html, dest=buffer)
                buffer.seek(0)
                if not pisa_status.err:
                    pdf_dir = os.path.join(settings.MEDIA_ROOT, 'prescriptions')
                    os.makedirs(pdf_dir, exist_ok=True)
                    filename = f'prescription_{prescription.pk}.pdf'
                    pdf_path = os.path.join(pdf_dir, filename)
                    with open(pdf_path, 'wb') as pdf_file:
                        pdf_file.write(buffer.getvalue())
                    prescription.pdf_file.name = f'prescriptions/{filename}'
                    prescription.save(update_fields=['pdf_file'])
                else:
                    logger.error("PDF generation error for prescription %s", prescription.pk)
            except Exception as e:
                logger.error("Exception during PDF generation for prescription %s: %s", prescription.pk, e)
            finally:
                buffer.close()

            messages.success(request, "✅ Prescription saved successfully.")

            # 5) Redirect to next appointment or list
            next_appointment = (
                Appointment.objects
                .filter(
                    doctor=appointment.doctor,
                    scheduled_time__date=appointment.scheduled_time.date(),
                    scheduled_time__gt=appointment.scheduled_time
                )
                .exclude(prescription__isnull=False)
                .order_by('scheduled_time')
                .first()
            )
            if next_appointment:
                return redirect('prescription:create', appointment_id=next_appointment.pk)
            return redirect('prescription:list')

        messages.error(request, "❌ There were errors in the form. Please correct them and try again.")
    else:
        form = PrescriptionForm(appointment_id=appointment.id)
        med_formset = MedicationFormSet(instance=None)

    return render(request, 'prescription/prescription_create.html', {
        'form': form,
        'medication_formset': med_formset,
        'appointment': appointment,
        'editing': False,
    })


@login_required
def prescription_detail(request, pk):
    """
    Display the details of a saved prescription.
    """
    prescription = get_object_or_404(Prescription, pk=pk)
    return render(request, 'prescription/prescription_detail.html', {
        'prescription': prescription
    })


@login_required
def edit_prescription(request, pk):
    """
    Handle editing of an existing prescription and its medications.
    """
    prescription = get_object_or_404(Prescription, pk=pk)

    if request.method == 'POST':
        form = PrescriptionForm(request.POST, request.FILES, instance=prescription)
        formset = MedicationFormSet(request.POST, request.FILES, instance=prescription)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, "✅ Prescription updated successfully.")
            return redirect('prescription:prescription_detail', pk=prescription.pk)
        messages.error(request, "❌ There were errors updating the prescription. Please check the fields.")
    else:
        form = PrescriptionForm(instance=prescription)
        formset = MedicationFormSet(instance=prescription)

    return render(request, 'prescription/prescription_create.html', {
        'form': form,
        'medication_formset': formset,
        'appointment': prescription.appointment,
        'editing': True,
    })


@login_required
def delete_prescription(request, pk):
    """
    Delete a prescription and redirect back to the list view.
    """
    prescription = get_object_or_404(Prescription, pk=pk)
    prescription.delete()
    messages.success(request, "🗑️ Prescription deleted successfully.")
    return redirect('prescription:list')


@login_required
def download_pdf_prescription(request, pk):
    """
    Serve the prescription PDF as a file download.
    """
    prescription = get_object_or_404(Prescription, pk=pk)
    html = render_to_string('prescription/pdf_template.html', {'prescription': prescription})
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="prescription_{pk}.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        messages.error(request, "❌ Error generating PDF.")
        logger.error("PDF download error for prescription %s", pk)
    return response


@login_required
def send_prescription_whatsapp(request, pk):
    """
    Redirect the user to WhatsApp with a pre-filled prescription message.
    """
    prescription = get_object_or_404(Prescription, pk=pk)
    pres_url = request.build_absolute_uri(prescription.get_absolute_url())
    voice_url = prescription.voice_note.url if prescription.voice_note else ''
    message = (
        f"📄 Prescription from Dr. {prescription.doctor.user.get_full_name()}\n"
        f"👤 Patient: {prescription.patient_full_name}, Age: {prescription.age}\n"
        f"📅 Date: {prescription.date_issued.strftime('%Y-%m-%d %H:%M')}\n"
        f"🎷 Voice Note: {voice_url}\n"
        f"🔗 View: {pres_url}"
    )
    return redirect(f"https://wa.me/?text={quote(message)}")
