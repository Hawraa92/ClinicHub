import json
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.utils.timezone import localtime
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.db.models import Prefetch, Sum
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

from .forms import AppointmentForm, PatientBookingForm
from .models import Appointment, PatientBookingRequest
from doctor.models import Doctor
from patient.forms import SecretaryPatientForm
from patient.models import Patient


def secretary_required(view_func):
    """
    Decorator to ensure the user is a logged-in secretary.
    """
    @login_required
    def _wrapped(request, *args, **kwargs):
        if getattr(request.user, 'role', None) != 'secretary':
            return HttpResponseForbidden("You do not have permission to access this page.")
        return view_func(request, *args, **kwargs)
    return _wrapped


@secretary_required
@require_GET
def secretary_dashboard(request):
    """
    Display the secretary's dashboard with today's stats and weekly overview.
    """
    today = timezone.localdate()
    appointment_form = AppointmentForm()
    patient_form = SecretaryPatientForm()

    qs = Appointment.objects.select_related('patient', 'doctor__user').order_by('-scheduled_time')
    todays_appointments = qs.filter(scheduled_time__date=today)
    patients_today = Patient.objects.filter(created_at__date=today).count()
    appointments_today = todays_appointments.count()
    revenue_today = todays_appointments.aggregate(total=Sum('iqd_amount'))['total'] or 0

    start_week = today - timedelta(days=today.weekday())
    week_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    week_counts = [
        qs.filter(scheduled_time__date=start_week + timedelta(days=i)).count()
        for i in range(7)
    ]

    context = {
        'appointment_form': appointment_form,
        'patient_form': patient_form,
        'appointments': qs,
        'today_appointments': todays_appointments,
        'stats': {
            'patients_today': patients_today,
            'appointments_today': appointments_today,
            'revenue_today_iqd': revenue_today,
        },
        'chart_data_json': json.dumps({'labels': week_days, 'data': week_counts}),
    }
    return render(request, 'appointments/secretary_dashboard.html', context)


@secretary_required
@require_http_methods(["GET", "POST"])
def create_appointment(request):
    """
    Handle creation of a new appointment via the secretary interface.
    """
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appt = form.save()
            messages.success(
                request,
                f"✅ Appointment booked for {appt.patient.full_name} "
                f"with Dr. {appt.doctor.user.get_full_name()} "
                f"at {appt.scheduled_time:%I:%M %p}."
            )
            return redirect('appointments:appointment_ticket', pk=appt.pk)
        messages.error(request, "❌ Please correct the errors below.")
    else:
        form = AppointmentForm()

    return render(request, 'appointments/create_appointment.html', {'form': form})


@secretary_required
@require_GET
def appointment_ticket(request, pk):
    """
    Render a ticket view for a confirmed appointment.
    """
    appointment = get_object_or_404(Appointment, pk=pk)
    context = {
        'appointment': appointment,
        'doctor_name': appointment.doctor.user.get_full_name() or appointment.doctor.user.username,
        'doctor_spec': getattr(appointment.doctor, 'specialization', ''),
        'secretary_name': request.user.get_full_name() or request.user.username,
    }
    return render(request, 'appointments/appointment_ticket.html', context)


@secretary_required
@require_http_methods(["GET", "POST"])
def edit_appointment(request, pk):
    """
    Display and process the form to edit an existing appointment.
    """
    appt = get_object_or_404(Appointment, pk=pk)
    if request.method == 'POST':
        form = AppointmentForm(request.POST, instance=appt)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Appointment updated successfully.")
            return redirect('appointments:appointment_list')
        messages.error(request, "❌ Please correct the errors below.")
    else:
        form = AppointmentForm(instance=appt)

    return render(request, 'appointments/edit_appointment.html', {
        'form': form,
        'appointment': appt
    })


@secretary_required
@require_http_methods(["GET", "POST"])
def delete_appointment(request, pk):
    """
    Confirm and delete an existing appointment.
    """
    appt = get_object_or_404(Appointment, pk=pk)
    if request.method == 'POST':
        appt.delete()
        messages.success(request, "🗑️ Appointment deleted successfully.")
        return redirect('appointments:appointment_list')
    return render(request, 'appointments/delete_confirmation.html', {'appointment': appt})


@secretary_required
@require_GET
def appointment_list(request):
    """
    List all appointments with optional search, sorting, and pagination.
    """
    sort = request.GET.get('sort', 'scheduled_time')
    if sort not in ['patient', 'doctor', 'scheduled_time']:
        sort = 'scheduled_time'
    search_query = request.GET.get('q', '')

    qs = Appointment.objects.select_related('patient', 'doctor__user')
    if search_query:
        qs = qs.filter(patient__full_name__icontains=search_query)
    qs = qs.order_by(sort)

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'appointments/appointment_list.html', {
        'appointments': page_obj,
        'search_query': search_query,
        'current_sort': sort,
    })


# ================== Public Booking ===================

@require_http_methods(["GET", "POST"])
def book_appointment_public(request):
    """
    Handle public booking requests from non-registered patients.
    """
    if request.method == "POST":
        form = PatientBookingForm(request.POST)
        if form.is_valid():
            booking = form.save()
            messages.success(
                request,
                f"✅ Thank you {booking.full_name}. Your appointment request has been received!"
            )
            return redirect('appointments:book_success')
        messages.error(request, "❌ Please correct the errors and try again.")
    else:
        form = PatientBookingForm()
    return render(request, 'appointments/book_appointment.html', {'form': form})


@require_GET
def book_success(request):
    """
    Render a success page after public booking.
    """
    return render(request, 'appointments/book_success.html')


@secretary_required
@require_GET
def new_booking_requests_api(request):
    """
    API endpoint to fetch new public booking requests (status='pending'),
    returning scheduled_time in local (Asia/Baghdad) timezone.
    """
    pending_requests = PatientBookingRequest.objects.filter(status='pending').order_by('-submitted_at')
    data = []
    for req in pending_requests:
        local_dt = localtime(req.scheduled_time)
        data.append({
            'id': req.id,
            'full_name': req.full_name,
            'requested_doctor': req.doctor.user.get_full_name(),
            'requested_time': local_dt.isoformat(),
            'status': req.status,
        })
    return JsonResponse({'booking_requests': data})


# ================== Queue Handling ===================

def get_queue_data():
    """
    Internal helper: build queue information for all doctors for today.
    """
    today = timezone.localdate()
    doctors = Doctor.objects.select_related('user').prefetch_related(
        Prefetch(
            'appointment_set',
            queryset=Appointment.objects.filter(
                scheduled_time__date=today,
                status='pending'
            ).order_by('scheduled_time').select_related('patient'),
            to_attr='today_appointments'
        )
    )

    queue_list = []
    for doc in doctors:
        appointments = getattr(doc, 'today_appointments', [])
        current = None
        waiting_list = []

        if appointments:
            first = appointments[0]
            current = {
                'id': first.id,
                'number': f"P-{first.queue_number:03d}",
                'patient_name': first.patient.full_name,
                'time': first.scheduled_time.strftime('%H:%M'),
            }
            for appt in appointments[1:]:
                waiting_list.append({
                    'id': appt.id,
                    'number': f"P-{appt.queue_number:03d}",
                    'patient_name': appt.patient.full_name,
                    'time': appt.scheduled_time.strftime('%H:%M'),
                })

        queue_list.append({
            'doctor_id': doc.id,
            'doctor_name': doc.user.get_full_name() or doc.user.username,
            'doctor_specialty': getattr(doc, 'specialization', ''),
            'status': 'available' if appointments else 'on_break',
            'current_patient': current,
            'waiting_list': waiting_list,
            'avg_time': 15,
            'department': getattr(doc, 'department', ''),
        })

    return queue_list


@require_GET
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def queue_display(request):
    """
    Render the public queue display screen.
    """
    queues = get_queue_data()
    return render(request, 'appointments/queue_display.html', {'queues': queues})


@secretary_required
@require_GET
def queue_number_api(request):
    """
    API endpoint returning JSON with current queue info for secretaries.
    """
    return JsonResponse({'queues': get_queue_data()})


@secretary_required
@require_POST
def call_next_api(request, doctor_id):
    """
    Move the next patient in queue to 'completed' status and return updated queue.
    """
    today = timezone.localdate()
    next_appt = Appointment.objects.filter(
        doctor_id=doctor_id,
        scheduled_time__date=today,
        status='pending'
    ).order_by('scheduled_time').first()

    if not next_appt:
        return JsonResponse({'error': 'No pending appointments for this doctor.'}, status=404)

    next_appt.status = 'completed'
    next_appt.save()
    return JsonResponse({'queues': get_queue_data()})


@secretary_required
@require_GET
def current_patient_api(request):
    """
    API endpoint returning current and next patient details.
    """    
    today = timezone.localdate()
    now = timezone.now()
    pending = list(
        Appointment.objects.filter(
            scheduled_time__date=today,
            status='pending'
        ).order_by('scheduled_time').select_related('patient', 'doctor__user')
    )

    current = None
    next_patient = None

    if pending:
        p0 = pending[0]
        wait_minutes = max(0, int((now - p0.scheduled_time).total_seconds() // 60))
        current = {
            'id': p0.id,
            'number': p0.queue_number,
            'patient_name': p0.patient.full_name,
            'doctor_name': p0.doctor.user.get_full_name(),
            'wait_time_minutes': wait_minutes,
        }

    if len(pending) > 1:
        p1 = pending[1]
        wait_minutes = max(0, int((now - p1.scheduled_time).total_seconds() // 60))
        next_patient = {
            'id': p1.id,
            'number': p1.queue_number,
            'patient_name': p1.patient.full_name,
            'doctor_name': p1.doctor.user.get_full_name(),
            'wait_time_minutes': wait_minutes,
        }

    return JsonResponse({'current_patient': current, 'next_patient': next_patient})


@secretary_required
@require_http_methods(["GET", "POST"])
def secretary_settings(request):
    """
    Render and process the secretary's settings page.
    """
    if request.method == 'POST':
        messages.success(request, "✅ Settings saved successfully.")
        return redirect('appointments:secretary_settings')
    return render(request, 'appointments/secretary_settings.html')
