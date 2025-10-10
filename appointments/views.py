# appointments/views.py
from __future__ import annotations

import base64
import csv
import io
import json
from datetime import timedelta, date
from functools import wraps

import qrcode
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseForbidden,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.timezone import get_default_timezone, localtime, make_aware
from django.views.decorators.cache import cache_control
from django.views.decorators.http import (
    require_GET,
    require_POST,
    require_http_methods,
)

from accounts.forms import CustomPasswordForm, ProfileUpdateForm
from doctor.models import Doctor
from patient.forms import SecretaryPatientForm
from patient.models import Patient

from .forms import AppointmentForm, PatientBookingForm
from .models import Appointment, AppointmentStatus, PatientBookingRequest

# Optional BookingRequestStatus for lighter builds
try:
    from .models import BookingRequestStatus
except Exception:  # pragma: no cover
    BookingRequestStatus = None  # type: ignore

# Optional XLSX export
try:
    import openpyxl  # type: ignore
    _HAS_OPENPYXL = True
except Exception:  # pragma: no cover
    _HAS_OPENPYXL = False


# ------------------------------------------------------------------#
#                           Helpers                                  #
# ------------------------------------------------------------------#
_LOCAL_TZ = get_default_timezone()


def _json_success(data) -> JsonResponse:
    return JsonResponse({"success": True, **data})


def _json_error(msg, *, status=400):
    return JsonResponse({"success": False, "error": msg}, status=status)


def _today():
    return timezone.localdate()


def _doctor_name(doc: Doctor) -> str:
    return (
        getattr(doc, "get_display_name", lambda: "")()
        or getattr(doc, "full_name", "")
        or doc.user.get_full_name()
        or doc.user.first_name
        or (doc.user.username.split("@")[0] if "@" in doc.user.username else doc.user.username)
        or "Doctor"
    )


def _user_name(u) -> str:
    return (
        u.get_full_name()
        or u.first_name
        or (u.username.split("@")[0] if "@" in u.username else u.username)
        or "User"
    )


def _to_local_aware(dt):
    """Normalize naive datetimes to local TZ without changing the wall clock."""
    if dt is None:
        return None
    if timezone.is_naive(dt):
        return make_aware(dt, _LOCAL_TZ)
    return dt.astimezone(_LOCAL_TZ)


def _model_has_field(model, field_name: str) -> bool:
    try:
        return any(getattr(f, "name", "") == field_name for f in model._meta.get_fields())  # type: ignore[attr-defined]
    except Exception:
        return False


def secretary_required(view):
    @wraps(view)
    @login_required
    def wrapper(request, *a, **kw):
        if getattr(request.user, "role", None) != "secretary" and not request.user.is_superuser:
            return HttpResponseForbidden("You do not have permission to access this page.")
        return view(request, *a, **kw)
    return wrapper


def is_patient(user) -> bool:
    return getattr(user, "role", None) == "patient"


# ------------------------------------------------------------------#
#                     Secretary Dashboard                           #
# ------------------------------------------------------------------#
@secretary_required
@require_GET
def secretary_dashboard(request: HttpRequest):
    today = _today()
    base = Appointment.objects.select_related("patient", "doctor__user")

    todays = base.filter(scheduled_time__date=today)

    stats = {
        "patients_today": base.filter(scheduled_time__date=today).values("patient_id").distinct().count(),
        "new_patients_today": Patient.objects.filter(created_at__date=today).count(),
        "total_patients": Patient.objects.count(),
        "appointments_today": todays.count(),
        "revenue_today_iqd": todays.aggregate(total=Sum("iqd_amount")).get("total") or 0,
    }

    week_start = today - timedelta(days=today.weekday())
    rows = (
        base.filter(scheduled_time__date__range=[week_start, week_start + timedelta(days=6)])
        .annotate(day=TruncDate("scheduled_time"))
        .values("day")
        .annotate(count=Count("id"))
    )
    counts = {r["day"]: r["count"] for r in rows}
    labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    chart = [counts.get(week_start + timedelta(days=i), 0) for i in range(7)]

    ctx = {
        "appointment_form": AppointmentForm(),
        "patient_form": SecretaryPatientForm(),
        "appointments": base.order_by("-scheduled_time")[:20],
        "today_appointments": todays,
        "stats": stats,
        "chart_data_json": json.dumps({"labels": labels, "data": chart}),
    }
    return render(request, "appointments/secretary_dashboard.html", ctx)


# ------------------------------------------------------------------#
#                        Appointment CRUD                           #
# ------------------------------------------------------------------#
@secretary_required
@require_http_methods(["GET", "POST"])
def create_appointment(request: HttpRequest):
    """
    Secretary-created appointments are APPROVED immediately
    and get an auto-generated queue_number for that doctor/day.
    """
    form = AppointmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        appt: Appointment = form.save(commit=False)
        appt.scheduled_time = _to_local_aware(appt.scheduled_time)

        # ✅ Approve directly (ignore any status coming from the form)
        appt.status = getattr(AppointmentStatus, "APPROVED", AppointmentStatus.PENDING)

        # Auto queue number for that doctor on that date (transaction-safe)
        if appt.scheduled_time and appt.queue_number is None:
            with transaction.atomic():
                count_today = (
                    Appointment.objects.select_for_update()
                    .filter(
                        doctor=appt.doctor,
                        scheduled_time__date=appt.scheduled_time.date(),
                    )
                    .count()
                )
                appt.queue_number = count_today + 1
                appt.save()
        else:
            appt.save()

        messages.success(
            request,
            f"✅ Appointment booked for {appt.patient.full_name} "
            f"with Dr. {_doctor_name(appt.doctor)} "
            f"at {localtime(appt.scheduled_time):%I:%M %p}.",
        )
        return redirect("appointments:appointment_ticket", pk=appt.pk)
    elif request.method == "POST":
        messages.error(request, "❌ Please correct the errors below.")
    return render(request, "appointments/create_appointment.html", {"form": form})


@secretary_required
@require_GET
def appointment_ticket(request, pk):
    appt = get_object_or_404(
        Appointment.objects.select_related("doctor__user", "patient"), pk=pk
    )

    qr = qrcode.make(request.build_absolute_uri(), box_size=6, border=2)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")

    ctx = {
        "appointment": appt,
        "doctor_name": _doctor_name(appt.doctor),
        "doctor_spec": getattr(appt.doctor, "specialty", ""),
        "secretary_name": _user_name(request.user),
        "qr_code": base64.b64encode(buf.getvalue()).decode(),
    }
    return render(request, "appointments/appointment_ticket.html", ctx)


@secretary_required
@require_http_methods(["GET", "POST"])
def edit_appointment(request, pk):
    appt = get_object_or_404(Appointment, pk=pk)
    form = AppointmentForm(request.POST or None, instance=appt)
    if request.method == "POST" and form.is_valid():
        appt = form.save(commit=False)
        appt.scheduled_time = _to_local_aware(appt.scheduled_time)
        appt.save()
        messages.success(request, "✅ Appointment updated successfully.")
        return redirect("appointments:appointment_list")
    elif request.method == "POST":
        messages.error(request, "❌ Please correct the errors below.")
    return render(request, "appointments/edit_appointment.html", {"form": form, "appointment": appt})


@secretary_required
@require_http_methods(["GET", "POST"])
def cancel_appointment(request, pk: int):
    """Soft cancel: forbid COMPLETED; set status=CANCELLED."""
    appt = get_object_or_404(Appointment, pk=pk)

    if appt.status == AppointmentStatus.COMPLETED:
        messages.error(request, "❌ Cannot cancel a completed appointment.")
        return redirect("appointments:appointment_list")

    if request.method == "POST":
        reason = (request.POST.get("reason") or "").strip()

        new_notes = appt.notes or ""
        if reason:
            stamp = timezone.localtime().strftime("%Y-%m-%d %H:%M")
            user_display = request.user.get_full_name() or request.user.username
            note_line = f"[Cancelled {stamp} by {user_display}] {reason}"
            new_notes = f"{new_notes}\n{note_line}" if new_notes else note_line

        update_kwargs = {"status": AppointmentStatus.CANCELLED}
        if reason:
            update_kwargs["notes"] = new_notes
        Appointment.objects.filter(pk=appt.pk).update(**update_kwargs)

        messages.success(request, "✅ Appointment cancelled successfully.")
        return redirect("appointments:appointment_list")

    return render(request, "appointments/delete_confirmation.html", {"appointment": appt})


@secretary_required
@require_http_methods(["GET", "POST"])
def delete_appointment(request, pk):
    """Hard delete — admins only."""
    appt = get_object_or_404(Appointment, pk=pk)
    if not request.user.is_superuser:
        messages.error(request, "❌ Only administrators can delete appointments permanently.")
        return redirect("appointments:appointment_list")

    if request.method == "POST":
        appt.delete()
        messages.success(request, "🗑️ Appointment deleted permanently.")
        return redirect("appointments:appointment_list")
    return render(request, "appointments/delete_confirmation.html", {"appointment": appt})


@secretary_required
@require_GET
def appointment_list(request):
    sort = request.GET.get("sort", "scheduled_time")
    fld = {
        "patient": "patient__full_name",
        "doctor": "doctor__user__first_name",
        "scheduled_time": "scheduled_time",
    }.get(sort, "scheduled_time")

    qs = Appointment.objects.select_related("patient", "doctor__user")

    # ✅ Default: show ALL (no status filter)
    status_key = (request.GET.get("status") or "all").lower()
    status_map = {
        "pending": AppointmentStatus.PENDING,
        "approved": getattr(AppointmentStatus, "APPROVED", AppointmentStatus.PENDING),
        "completed": AppointmentStatus.COMPLETED,
        "cancelled": AppointmentStatus.CANCELLED,
    }
    if status_key in status_map:
        qs = qs.filter(status=status_map[status_key])

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(patient__full_name__icontains=q)
            | Q(doctor__user__first_name__icontains=q)
            | Q(doctor__user__last_name__icontains=q)
            | Q(notes__icontains=q)
        )
    page = Paginator(qs.order_by(f"-{fld}"), 10).get_page(request.GET.get("page"))
    return render(
        request,
        "appointments/appointment_list.html",
        {"appointments": page, "search_query": q, "current_sort": sort, "current_status": status_key},
    )


# ------------------------------------------------------------------#
#                Patient Portal Booking (IN-APP)                    #
# ------------------------------------------------------------------#
class _PatientPortalBookingForm(forms.ModelForm):
    """Minimal form for logged-in patients: choose time only."""
    class Meta:
        model = Appointment
        fields = ["scheduled_time"]
        widgets = {"scheduled_time": forms.DateTimeInput(attrs={"type": "datetime-local"})}

    def __init__(self, *args, doctor=None, **kwargs):
        self.doctor = doctor
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        st = cleaned.get("scheduled_time")
        if st and st <= timezone.now():
            self.add_error("scheduled_time", "Please choose a future time.")
        # Do not block conflicts here; secretary will finalize actual slot
        return cleaned


@login_required
@require_http_methods(["GET", "POST"])
def book_patient(request, doctor_id: int):
    """
    Patient books INSIDE the portal:
    - If BookingRequestStatus exists, create PatientBookingRequest (PENDING).
    - Otherwise, fallback to creating an Appointment with PENDING.
    """
    if not is_patient(request.user):
        return HttpResponseForbidden("Patients only.")

    doctor = get_object_or_404(Doctor, pk=doctor_id)
    patient = get_object_or_404(Patient, user=request.user)

    if request.method == "POST":
        form = _PatientPortalBookingForm(request.POST, doctor=doctor)
        if form.is_valid():
            sched = _to_local_aware(form.cleaned_data["scheduled_time"])

            if BookingRequestStatus:
                # Create a booking request (does NOT block the slot yet)
                full_name = patient.full_name or request.user.get_full_name() or request.user.username
                contact = getattr(patient, "phone", "") or getattr(patient, "mobile", "") or request.user.email or ""
                dob = getattr(patient, "date_of_birth", None)

                br_kwargs = dict(
                    doctor=doctor,
                    full_name=full_name,
                    contact_info=contact,
                    date_of_birth=dob,
                    scheduled_time=sched,
                    status=BookingRequestStatus.PENDING,
                )
                # Attach patient/user if model supports these fields
                if _model_has_field(PatientBookingRequest, "patient"):
                    br_kwargs["patient"] = patient
                if _model_has_field(PatientBookingRequest, "user"):
                    br_kwargs["user"] = request.user

                PatientBookingRequest.objects.create(**br_kwargs)

                # Notify secretaries
                try:
                    from notifications.models import Notification
                    Notification.objects.create(
                        to_role="secretary",
                        title="New booking request",
                        message=f"{full_name} requested {_doctor_name(doctor)} at {localtime(sched):%Y-%m-%d %H:%M}",
                        link="/appointments/secretary/",  # dashboard bell
                    )
                except Exception:
                    pass

                messages.success(request, "Your request was sent and is pending secretary approval.")
                # No actual appointment yet
                return redirect("patient:dashboard")

            else:
                # Fallback: create a real Appointment as PENDING
                appt: Appointment = Appointment(
                    patient=patient,
                    doctor=doctor,
                    scheduled_time=sched,
                    status=getattr(AppointmentStatus, "PENDING", "pending"),
                    queue_number=None,
                )
                appt.save()
                try:
                    from notifications.models import Notification
                    Notification.objects.create(
                        to_role="secretary",
                        title="New appointment request",
                        message=f"{patient.full_name} requested {_doctor_name(doctor)} at {localtime(sched):%Y-%m-%d %H:%M}",
                        link="/appointments/secretary/appointments/?status=pending",
                    )
                except Exception:
                    pass
                messages.success(request, "Your request was sent and is pending approval.")
                return redirect("appointments:my_appointments")
    else:
        form = _PatientPortalBookingForm(doctor=doctor)

    return render(
        request,
        "appointments/book_patient.html",
        {"form": form, "doctor": doctor, "patient": patient},
    )


@login_required
@require_GET
def my_appointments(request):
    """
    Show actual Appointments + (if enabled) PENDING PatientBookingRequests
    that belong to the logged-in patient.
    """
    if not is_patient(request.user):
        return HttpResponseForbidden("Patients only.")

    patient = get_object_or_404(Patient, user=request.user)

    # Actual appointments
    appointments = (
        Appointment.objects
        .filter(patient=patient)
        .select_related("doctor", "doctor__user")
        .order_by("-scheduled_time")
    )

    # Pending booking requests (best-effort match)
    booking_requests = []
    if BookingRequestStatus:
        q = PatientBookingRequest.objects.filter(status=BookingRequestStatus.PENDING)

        if _model_has_field(PatientBookingRequest, "patient"):
            q = q.filter(patient=patient)
        elif _model_has_field(PatientBookingRequest, "user"):
            q = q.filter(user=request.user)
        else:
            # Heuristic match by contact/name/email/phone
            lookups = Q()
            phone = getattr(patient, "phone", None) or getattr(patient, "mobile", None)
            if phone:
                lookups |= Q(contact_info__icontains=phone)
            if request.user.email:
                lookups |= Q(contact_info__icontains=request.user.email)
            display_name = patient.full_name or request.user.get_full_name() or request.user.username
            if display_name:
                lookups |= Q(full_name__icontains=display_name)
            q = q.filter(lookups)

        has_submitted_at = _model_has_field(PatientBookingRequest, "submitted_at")
        q = q.select_related("doctor", "doctor__user").order_by("-submitted_at" if has_submitted_at else "-scheduled_time")
        booking_requests = list(q[:20])

    return render(
        request,
        "appointments/my_appointments.html",
        {"appointments": appointments, "booking_requests": booking_requests},
    )


@secretary_required
@require_POST
def approve_appointment(request, pk: int):
    """Approve an Appointment: set status and generate queue_number if missing."""
    appt = get_object_or_404(Appointment, pk=pk)

    if appt.status != AppointmentStatus.COMPLETED:
        with transaction.atomic():
            new_status = getattr(AppointmentStatus, "APPROVED", AppointmentStatus.PENDING)
            appt.status = new_status
            if appt.queue_number is None and appt.scheduled_time:
                count_today = (
                    Appointment.objects.select_for_update()
                    .filter(doctor=appt.doctor, scheduled_time__date=appt.scheduled_time.date())
                    .count()
                )
                appt.queue_number = count_today + 1
            appt.save()

    messages.success(request, "Appointment approved.")
    return redirect("appointments:appointment_list")


# Optional: approve a booking request and convert it into an Appointment
@secretary_required
@require_POST
def approve_booking_request(request, pk: int):
    """Convert a PatientBookingRequest -> Appointment and mark request as approved."""
    if not BookingRequestStatus:
        return _json_error("Booking requests are not enabled.", status=400)

    br = get_object_or_404(PatientBookingRequest, pk=pk)

    # Find patient
    patient_obj: Patient | None = None
    if _model_has_field(PatientBookingRequest, "patient") and getattr(br, "patient", None):
        patient_obj = br.patient  # type: ignore[attr-defined]
    elif _model_has_field(PatientBookingRequest, "user") and getattr(br, "user", None):
        patient_obj = Patient.objects.filter(user=br.user).first()  # type: ignore[attr-defined]
    if not patient_obj:
        # fallback heuristic by name/email/phone
        qs = Patient.objects.all()
        if getattr(br, "contact_info", None):
            qs = qs.filter(
                Q(phone__icontains=br.contact_info)
                | Q(mobile__icontains=br.contact_info)
                | Q(user__email__iexact=br.contact_info)
            )
        if not qs.exists() and getattr(br, "full_name", None):
            qs = Patient.objects.filter(full_name__icontains=br.full_name)
        patient_obj = qs.first()

    if not patient_obj:
        messages.error(request, "Cannot approve: patient record not linked/found. Please convert manually.")
        return redirect("appointments:secretary_dashboard")

    with transaction.atomic():
        Appointment.objects.create(
            patient=patient_obj,
            doctor=br.doctor,
            scheduled_time=_to_local_aware(br.scheduled_time),
            status=getattr(AppointmentStatus, "APPROVED", AppointmentStatus.PENDING),
        )
        # Mark request approved
        try:
            br.status = getattr(BookingRequestStatus, "APPROVED", BookingRequestStatus.PENDING)
            br.save(update_fields=["status"])
        except Exception:
            pass

    messages.success(request, "Booking request approved and appointment created.")
    return redirect("appointments:appointment_list")


# ------------------------------------------------------------------#
#                  Public Booking (kept for urls.py)                #
# ------------------------------------------------------------------#
@require_http_methods(["GET", "POST"])
def book_appointment_public(request, doctor_id=None):
    """Public booking (not logged-in): saves PatientBookingRequest, not Appointment."""
    # Determine doctor from path or query
    doctor_inst = None
    try:
        doctor_inst = (
            Doctor.objects.get(pk=doctor_id) if doctor_id else Doctor.objects.get(pk=request.GET.get("doctor_id"))
        )
    except (Doctor.DoesNotExist, ValueError, TypeError):
        doctor_inst = None

    # Honeypot against spam
    if request.method == "POST" and request.POST.get("hp_field"):
        return redirect("appointments:book_success")

    if request.method == "POST":
        data = request.POST.copy()
        if doctor_inst and "doctor" not in data:
            data["doctor"] = doctor_inst.pk
        form = PatientBookingForm(data)
        if doctor_inst:
            form.instance.doctor = doctor_inst
        if form.is_valid():
            br = form.save(commit=False)
            br.scheduled_time = _to_local_aware(br.scheduled_time)
            br.save()
            messages.success(request, f"✅ Thank you {br.full_name}, we received your request.")
            return redirect("appointments:book_success")
        messages.error(request, "❌ Please fix the errors below.")
    else:
        form = PatientBookingForm(initial={"doctor": doctor_inst} if doctor_inst else {})
        if doctor_inst and "doctor" in form.fields:
            form.fields["doctor"].disabled = True

    return render(
        request,
        "appointments/book_appointment.html",
        {"form": form, "doctor_instance": doctor_inst},
    )


@require_GET
def book_success(request):
    return render(request, "appointments/book_success.html")


# ------------------------------------------------------------------#
#                         Reports (Daily/Weekly/Monthly/Custom)     #
# ------------------------------------------------------------------#
def _period_bounds(request):
    """Compute date bounds based on ?period=day|week|month|custom."""
    today = _today()
    period = (request.GET.get("period") or "day").lower()
    start_str = request.GET.get("start")
    end_str = request.GET.get("end")

    if period == "custom" and start_str and end_str:
        try:
            start = date.fromisoformat(start_str)
            end = date.fromisoformat(end_str)
        except Exception:
            start, end = today, today
    elif period == "week":
        start = today - timedelta(days=today.weekday())  # Monday
        end = start + timedelta(days=6)
    elif period == "month":
        start = today.replace(day=1)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)
    else:  # day (default)
        start = end = today

    if end < start:
        start, end = end, start
    return (period, start, end)


@secretary_required
@require_GET
def secretary_reports(request):
    """Reports screen with summaries + table within a given period."""
    period, start, end = _period_bounds(request)

    base = (
        Appointment.objects.filter(scheduled_time__date__range=[start, end])
        .select_related("patient", "doctor__user")
    )

    total = base.count()
    status_rows = base.values("status").annotate(c=Count("id"))
    by_status = {r["status"]: r["c"] for r in status_rows}
    completed = by_status.get(AppointmentStatus.COMPLETED, 0)
    cancelled = by_status.get(AppointmentStatus.CANCELLED, 0)
    pending = by_status.get(AppointmentStatus.PENDING, 0)
    revenue = base.aggregate(total=Sum("iqd_amount"))["total"] or 0

    new_patients = Patient.objects.filter(created_at__date__range=[start, end]).count()

    daily_rows = (
        base.annotate(day=TruncDate("scheduled_time"))
        .values("day")
        .annotate(count=Count("id"), rev=Sum("iqd_amount"))
        .order_by("day")
    )
    daily = [{"day": r["day"], "count": r["count"], "revenue": r["rev"] or 0} for r in daily_rows]

    top_doctors = (
        base.values("doctor_id", "doctor__user__first_name", "doctor__user__last_name")
        .annotate(count=Count("id"), rev=Sum("iqd_amount"))
        .order_by("-count")[:10]
    )

    appointments = base.order_by("scheduled_time")

    ctx = {
        "period": period,
        "start": start,
        "end": end,
        "summary": {
            "total": total,
            "completed": completed,
            "cancelled": cancelled,
            "pending": pending,
            "revenue": revenue,
            "new_patients": new_patients,
        },
        "daily": daily,
        "top_doctors": top_doctors,
        "appointments": appointments,
    }
    return render(request, "appointments/secretary_reports.html", ctx)


@secretary_required
@require_GET
def reports_export(request):
    """Export same range as secretary_reports."""
    fmt = (request.GET.get("format") or "csv").lower()
    _, start, end = _period_bounds(request)

    qs = (
        Appointment.objects.filter(scheduled_time__date__range=[start, end])
        .select_related("patient", "doctor__user")
        .order_by("scheduled_time")
    )

    # CSV (UTF-8 with BOM)
    if fmt == "csv" or (fmt == "xlsx" and not _HAS_OPENPYXL):
        if fmt == "xlsx" and not _HAS_OPENPYXL:
            messages.warning(request, "Openpyxl not installed, falling back to CSV.")

        buff = io.StringIO()
        buff.write("\ufeff")  # BOM

        w = csv.writer(buff)
        w.writerow(["ID", "Scheduled Date", "Scheduled Time", "Patient", "Doctor", "Status", "Amount (IQD)", "Notes"])
        for a in qs:
            dt = localtime(a.scheduled_time)
            w.writerow([
                a.id,
                dt.strftime("%Y-%m-%d"),
                dt.strftime("%H:%M"),
                a.patient.full_name,
                _doctor_name(a.doctor),
                a.get_status_display(),
                a.iqd_amount or 0,
                (a.notes or "").replace("\n", " ").strip(),
            ])
        resp = HttpResponse(buff.getvalue(), content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="appointments_{start}_{end}.csv"'
        return resp

    # XLSX
    if fmt == "xlsx" and _HAS_OPENPYXL:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Appointments"
        try:
            ws.sheet_view.rightToLeft = True
        except Exception:
            pass

        headers = ["ID", "Scheduled Date", "Scheduled Time", "Patient", "Doctor", "Status", "Amount (IQD)", "Notes"]
        ws.append(headers)
        for a in qs:
            dt = localtime(a.scheduled_time)
            ws.append([
                a.id,
                dt.strftime("%Y-%m-%d"),
                dt.strftime("%H:%M"),
                a.patient.full_name,
                _doctor_name(a.doctor),
                a.get_status_display(),
                a.iqd_amount or 0,
                (a.notes or "").strip(),
            ])

        ws2 = wb.create_sheet("Summary")
        try:
            ws2.sheet_view.rightToLeft = True
        except Exception:
            pass

        total = qs.count()
        status_rows = qs.values("status").annotate(c=Count("id"))
        by_status = {r["status"]: r["c"] for r in status_rows}
        completed = by_status.get(AppointmentStatus.COMPLETED, 0)
        cancelled = by_status.get(AppointmentStatus.CANCELLED, 0)
        pending = by_status.get(AppointmentStatus.PENDING, 0)
        revenue = qs.aggregate(total=Sum("iqd_amount"))["total"] or 0
        new_patients = Patient.objects.filter(created_at__date__range=[start, end]).count()

        ws2.append(["Metric", "Value"])
        ws2.append(["Period Start", str(start)])
        ws2.append(["Period End", str(end)])
        ws2.append(["Total Appointments", total])
        ws2.append(["Completed", completed])
        ws2.append(["Cancelled", cancelled])
        ws2.append(["Pending", pending])
        ws2.append(["Revenue (IQD)", revenue])
        ws2.append(["New Patients", new_patients])

        out = io.BytesIO()
        wb.save(out)
        resp = HttpResponse(
            out.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        resp["Content-Disposition"] = f'attachment; filename="appointments_{start}_{end}.xlsx"'
        return resp

    messages.error(request, "Unsupported export format.")
    return redirect("appointments:secretary_reports")


# ------------------------------------------------------------------#
#                   Queue Display & APIs                            #
# ------------------------------------------------------------------#
def _queue_snapshot():
    """
    Build today's queues per doctor from PENDING appointments.
    Avoid relying on reverse related_name; derive doctors from today's appointments set.
    """
    today = _today()
    default_mins = getattr(settings, "APPOINTMENT_DURATION_MINUTES", 15)

    appts = (
        Appointment.objects.filter(scheduled_time__date=today, status=AppointmentStatus.PENDING)
        .select_related("patient", "doctor__user")
        .order_by("scheduled_time")
    )

    doctor_ids = sorted({a.doctor_id for a in appts})
    doctors = Doctor.objects.select_related("user").filter(id__in=doctor_ids).order_by("id")

    by_doc: dict[int, list[Appointment]] = {}
    for a in appts:
        by_doc.setdefault(a.doctor_id, []).append(a)

    queues = []
    for d in doctors:
        today_appts = by_doc.get(d.id, [])
        current, waiting = None, []
        if today_appts:
            first, rest = today_appts[0], today_appts[1:]
            current = {
                "id": first.id,
                "number": f"P-{first.queue_number:03d}" if first.queue_number else "-",
                "patient_name": first.patient.full_name,
                "time": first.scheduled_time.strftime("%H:%M"),
            }
            waiting = [
                {
                    "id": w.id,
                    "number": f"P-{w.queue_number:03d}" if w.queue_number else "-",
                    "patient_name": w.patient.full_name,
                    "time": w.scheduled_time.strftime("%H:%M"),
                }
                for w in rest
            ]
        queues.append(
            {
                "doctor_id": d.id,
                "doctor_name": _doctor_name(d),
                "status": "available" if today_appts else "on_break",
                "current_patient": current,
                "waiting_list": waiting,
                "avg_time": default_mins,
            }
        )
    return queues


@require_GET
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def queue_display(request):
    return render(request, "appointments/queue_display.html", {"queues": _queue_snapshot()})


@secretary_required
@require_GET
def queue_number_api(request):
    return _json_success({"queues": _queue_snapshot()})


@secretary_required
@require_POST
def call_next_api(request, doctor_id):
    """
    Mark next (or specific) PENDING appointment as COMPLETED for this doctor.
    Uses .save() to trigger signals; returns updated queues + updated appt info.
    """
    today = _today()
    appt_id = request.POST.get("appointment_id")

    with transaction.atomic():
        base_qs = (
            Appointment.objects.select_for_update()
            .filter(
                doctor_id=doctor_id,
                status=AppointmentStatus.PENDING,
                scheduled_time__date=today,
            )
            .order_by("scheduled_time")
        )

        nxt = None
        if appt_id:
            nxt = Appointment.objects.select_for_update().filter(pk=appt_id, doctor_id=doctor_id).first()
            if not nxt or nxt.status != AppointmentStatus.PENDING or (nxt.scheduled_time and nxt.scheduled_time.date() != today):
                nxt = base_qs.first()
        else:
            nxt = base_qs.first()

        if not nxt:
            return _json_error("No pending appointments.", status=404)

        nxt.status = AppointmentStatus.COMPLETED
        nxt.save(update_fields=["status"])  # trigger signals if any

    return _json_success({
        "updated": {
            "id": nxt.pk,
            "status": nxt.status,
            "patient": getattr(nxt.patient, "full_name", ""),
            "time": localtime(nxt.scheduled_time).strftime("%H:%M") if nxt.scheduled_time else "",
        },
        "queues": _queue_snapshot()
    })


@secretary_required
@require_GET
def current_patient_api(request):
    today = _today()
    now = timezone.now()

    pend = list(
        Appointment.objects.filter(scheduled_time__date=today, status=AppointmentStatus.PENDING)
        .order_by("scheduled_time")
        .select_related("patient", "doctor__user")
    )

    current = nxt = None
    if pend:
        p0 = pend[0]
        current = {
            "id": p0.id,
            "number": p0.queue_number,
            "patient_name": p0.patient.full_name,
            "doctor_name": _doctor_name(p0.doctor),
            "wait_time_minutes": max(0, int((now - p0.scheduled_time).total_seconds() // 60)),
        }
    if len(pend) > 1:
        p1 = pend[1]
        nxt = {
            "id": p1.id,
            "number": p1.queue_number,
            "patient_name": p1.patient.full_name,
            "doctor_name": _doctor_name(p1.doctor),
            "wait_time_minutes": max(0, int((now - p1.scheduled_time).total_seconds() // 60)),
        }
    return _json_success({"current_patient": current, "next_patient": nxt})


# ------------------------------------------------------------------#
#                   Secretary Settings & Polling                     #
# ------------------------------------------------------------------#
@secretary_required
@require_http_methods(["GET", "POST"])
def secretary_settings(request):
    user = request.user
    profile_form = ProfileUpdateForm(instance=user)
    password_form = CustomPasswordForm(user=user)

    if request.method == "POST":
        pw_post = {"old_password", "new_password1", "new_password2"} & set(request.POST.keys())

        if pw_post:
            password_form = CustomPasswordForm(user=user, data=request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "🔒 Password changed successfully.")
                return redirect("appointments:secretary_settings")
            messages.error(request, "❌ Please fix the password errors.")
        else:
            profile_form = ProfileUpdateForm(request.POST, instance=user)
            if profile_form.is_valid():
                changed = profile_form.changed_data
                profile_form.save()
                messages.success(
                    request,
                    f"✅ Profile updated ({', '.join(changed)})!" if changed else "ℹ No changes detected.",
                )
                return redirect("appointments:secretary_settings")
            messages.error(request, "❌ Please fix the profile errors.")

    return render(
        request,
        "appointments/secretary_settings.html",
        {"profile_form": profile_form, "password_form": password_form},
    )


@secretary_required
@require_GET
def new_booking_requests_api(request):
    """
    Bell counter API:
    - If a Notification model exists → count UNREAD notifications to secretaries only.
    - Else → count ONLY pending booking requests (NOT pending appointments).
    This decouples the bell from Next Call / queue status.
    """
    items: list[dict] = []
    # 1) Prefer dedicated Notification model if available
    try:
        from notifications.models import Notification as NotiModel  # type: ignore

        q = NotiModel.objects.all()
        # filter to secretary role if field exists
        if _model_has_field(NotiModel, "to_role"):
            q = q.filter(to_role="secretary")
        elif _model_has_field(NotiModel, "recipient_role"):
            q = q.filter(recipient_role="secretary")

        # unread-only if field exists; otherwise take all (best effort)
        if _model_has_field(NotiModel, "is_read"):
            q = q.filter(is_read=False)
        elif _model_has_field(NotiModel, "read_at"):
            q = q.filter(read_at__isnull=True)

        # order by most recent if possible
        if _model_has_field(NotiModel, "created_at"):
            q = q.order_by("-created_at")
        elif _model_has_field(NotiModel, "created"):
            q = q.order_by("-created")

        count = q.count()
        for n in q[:50]:
            title = getattr(n, "title", "") or getattr(n, "event", "") or "Notification"
            message = getattr(n, "message", "") or getattr(n, "text", "")
            link = getattr(n, "link", "") or getattr(n, "url", "")
            items.append({
                "id": n.pk,
                "title": str(title),
                "message": str(message),
                "link": str(link),
                "source": "notification",
            })
        return _json_success({"count": count, "booking_requests": items})
    except Exception:
        # Fall through to booking requests-only
        pass

    # 2) Fallback: ONLY pending booking requests (no appointments)
    if BookingRequestStatus:
        pending_reqs = (
            PatientBookingRequest.objects.filter(status=BookingRequestStatus.PENDING)
            .select_related("doctor__user")
        )
        if _model_has_field(PatientBookingRequest, "submitted_at"):
            pending_reqs = pending_reqs.order_by("-submitted_at")
        else:
            pending_reqs = pending_reqs.order_by("-scheduled_time")

        for r in pending_reqs[:50]:
            items.append({
                "id": r.id,
                "full_name": getattr(r, "full_name", ""),
                "requested_doctor": _doctor_name(r.doctor),
                "requested_time_display": localtime(r.scheduled_time).strftime("%Y-%m-%d %H:%M")
                    if getattr(r, "scheduled_time", None) else "",
                "status": getattr(r, "status", ""),
                "source": "request",
            })

    return _json_success({"count": len(items), "booking_requests": items})
