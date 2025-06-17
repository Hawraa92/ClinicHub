# appointments/views.py

import json
from datetime import date, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.db.models import Prefetch, Sum
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

from .forms import AppointmentForm
from .models import Appointment
from doctor.models import Doctor
from patient.forms import SecretaryPatientForm
from patient.models import Patient


def is_secretary(user):
    return getattr(user, 'role', None) == 'secretary'


@login_required
@require_GET
def secretary_dashboard(request):
    if not is_secretary(request.user):
        return redirect('home:index')

    today = date.today()
    appointment_form = AppointmentForm()
    patient_form = SecretaryPatientForm()

    qs = (
        Appointment.objects
        .select_related('patient', 'doctor__user')
        .order_by('-scheduled_time')
    )

    todays_schedule = qs.filter(scheduled_time__date=today)
    patients_today = Patient.objects.filter(created_at__date=today).count()
    appointments_today = todays_schedule.count()

    # ✔️ فقط جمع الإيرادات بالدينار
    revenue_agg = todays_schedule.aggregate(total_iqd=Sum('iqd_amount'))
    revenue_today_iqd = revenue_agg['total_iqd'] or 0

    start_week = today - timedelta(days=today.weekday())
    week_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    week_counts = [
        qs.filter(scheduled_time__date=start_week + timedelta(days=i)).count()
        for i in range(7)
    ]

    context = {
        'appointment_form':    appointment_form,
        'patient_form':        patient_form,
        'appointments':        qs,
        'today_appointments':  todays_schedule,
        'stats': {
            'patients_today':     patients_today,
            'appointments_today': appointments_today,
            'new_patients_today': patients_today,
            'revenue_today_iqd':  revenue_today_iqd,
        },
        'chart_data_json': json.dumps({'labels': week_days, 'data': week_counts}),
    }
    return render(request, 'appointments/secretary_dashboard.html', context)


@login_required
def create_appointment(request):
    if not is_secretary(request.user):
        return redirect('home:index')

    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appt = form.save()
            messages.success(
                request,
                f"✅ Appointment booked for {appt.patient.full_name} with Dr. {appt.doctor.user.get_full_name()} at {appt.scheduled_time:%I:%M %p}."
            )
            return redirect('appointments:appointment_ticket', pk=appt.pk)
        messages.error(request, "❌ Please correct the errors below.")
    else:
        form = AppointmentForm()

    return render(request, 'appointments/create_appointment.html', {'form': form})


@login_required
def appointment_ticket(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)

    # تجهيز بيانات الطبيب والسكرتير
    doctor_name    = appointment.doctor.user.get_full_name() or appointment.doctor.user.username
    doctor_spec    = getattr(appointment.doctor, 'specialization', '')
    secretary_name = request.user.get_full_name() or request.user.username

    return render(request, 'appointments/appointment_ticket.html', {
        'appointment':     appointment,
        'doctor_name':     doctor_name,
        'doctor_spec':     doctor_spec,
        'secretary_name':  secretary_name,
    })


@login_required
def edit_appointment(request, pk):
    if not is_secretary(request.user):
        return redirect('home:index')

    appt = get_object_or_404(Appointment, pk=pk)
    if request.method == 'POST':
        form = AppointmentForm(request.POST, instance=appt)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Appointment updated successfully.")
            return redirect('appointments:list')
        messages.error(request, "❌ Please correct the errors below.")
    else:
        form = AppointmentForm(instance=appt)

    return render(request, 'appointments/edit_appointment.html', {
        'form': form,
        'appointment': appt,
    })


@login_required
def delete_appointment(request, pk):
    if not is_secretary(request.user):
        return redirect('home:index')

    appt = get_object_or_404(Appointment, pk=pk)
    if request.method == 'POST':
        appt.delete()
        messages.success(request, "🗑️ Appointment deleted successfully.")
        return redirect('appointments:list')

    return render(request, 'appointments/delete_confirmation.html', {'appointment': appt})


@login_required
@require_GET
def appointment_list(request):
    if not is_secretary(request.user):
        return redirect('home:index')

    sort = request.GET.get('sort', 'scheduled_time')
    if sort not in ('patient', 'doctor', 'scheduled_time'):
        sort = 'scheduled_time'

    qs = Appointment.objects.select_related('patient', 'doctor__user')
    q = request.GET.get('q')
    if q:
        qs = qs.filter(patient__full_name__icontains=q)
    qs = qs.order_by(sort)

    paginator = Paginator(qs, 10)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)

    return render(request, 'appointments/appointment_list.html', {
        'appointments':  page_obj,
        'search_query':  q or '',
        'current_sort':  sort,
    })


# ================== Queue Data ===================

def get_queue_data():
    today = timezone.localdate()
    doctors = (
        Doctor.objects
        .select_related('user')
        .prefetch_related(
            Prefetch(
                'appointment_set',
                queryset=Appointment.objects.filter(
                    scheduled_time__date=today, status='pending'
                ).order_by('scheduled_time').select_related('patient'),
                to_attr='today_appts'
            )
        )
    )

    data = []
    for d in doctors:
        appts = getattr(d, 'today_appts', [])
        specialization = getattr(d, 'specialization', 'Specialist')
        department     = getattr(d, 'department',     'general')

        waiting_list = []
        for a in appts[1:]:
            waiting_list.append({
                "number": f"P-{a.queue_number:03d}" if a.queue_number else "",
                "name":   a.patient.full_name if a.patient else "",
                "case":   "normal",
                "time":   a.scheduled_time.strftime('%H:%M') if a.scheduled_time else "",
            })

        status = "available" if appts else "on-break"

        data.append({
            "doctor_id":       d.id,
            "doctor_name":     d.user.get_full_name() or d.user.username,
            "doctor_specialty":specialization,
            "status":          status,
            "currentPatient": {
                "number": f"P-{appts[0].queue_number:03d}" if appts else "",
                "name":   appts[0].patient.full_name if appts else "",
                "case":   "normal",
                "time":   appts[0].scheduled_time.strftime('%H:%M') if appts else "",
            } if appts else None,
            "waiting": waiting_list,
            "avgTime": 15,
            "department": department
        })
    return data


@require_GET
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def queue_display(request):
    queue_data = get_queue_data()
    doctor_name = queue_data[0]['doctor_name'] if queue_data else "Unknown Doctor"
    return render(request, 'appointments/queue_display.html', {
        'queues':      queue_data,
        'doctor_name': doctor_name,
    })


@login_required
@require_GET
def queue_number_api(request):
    if not is_secretary(request.user):
        return HttpResponseForbidden()
    try:
        return JsonResponse({'queues': get_queue_data()})
    except Exception:
        return JsonResponse({'error': 'Cannot fetch queue'}, status=500)


@login_required
@require_POST
def call_next_api(request, doctor_id):
    if not is_secretary(request.user):
        return HttpResponseForbidden()

    today = timezone.localdate()
    next_appt = (
        Appointment.objects
        .filter(doctor_id=doctor_id, scheduled_time__date=today, status='pending')
        .order_by('scheduled_time')
        .first()
    )
    if next_appt:
        next_appt.status = 'completed'
        next_appt.save()
    return JsonResponse({'queues': get_queue_data()})


@login_required
@require_GET
def current_patient_api(request):
    if not is_secretary(request.user):
        return HttpResponseForbidden()

    today = timezone.localdate()
    now   = timezone.now()
    pending = list(
        Appointment.objects.filter(
            scheduled_time__date=today, status='pending'
        ).order_by('scheduled_time')
    )

    def serialize(a):
        wait = max(0, int((now - a.scheduled_time).total_seconds() // 60))
        return {
            'number':    a.queue_number,
            'name':      a.patient.full_name,
            'type':      a.doctor.user.get_full_name(),
            'wait_time': wait,
        }

    current = serialize(pending[0]) if pending else None
    nxt     = serialize(pending[1]) if len(pending) > 1 else None

    return JsonResponse({'current': current, 'next': nxt})


@login_required
@require_http_methods(["GET", "POST"])
def secretary_settings(request):
    if not is_secretary(request.user):
        return redirect('home:index')

    if request.method == 'POST':
        messages.success(request, "Settings saved successfully.")
        return redirect('appointments:secretary_settings')

    return render(request, 'appointments/settings.html')
