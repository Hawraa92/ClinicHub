# home/views.py

from django.shortcuts import render
from django.utils import timezone
from doctor.models import Doctor
from appointments.models import Appointment
from patient.models import Patient
from prescription.models import Prescription  # عدّل المسار إن اختلف عندك

def home_view(request):
    # جلب جميع الأطباء النشطين
    doctors = Doctor.objects.filter(user__is_active=True)

    context = {
        'doctors': doctors,
    }

    # إذا الطبيب مسجّل وجلسة دخول
    if request.user.is_authenticated and getattr(request.user, 'role', None) == 'doctor':
        today = timezone.localdate()

        # مواعيد اليوم
        todays_appointments = Appointment.objects.filter(
            doctor__user=request.user,
            scheduled_time__date=today
        )

        # الرقم التالي في قائمة الانتظار
        if todays_appointments.exists():
            next_queue_number = todays_appointments.first().queue_number
        else:
            next_queue_number = None

        # أحدث ٥ ملفات مرضى أنشئت اليوم
        recent_patients = Patient.objects.filter(
            created_at__date=today
        ).order_by('-created_at')[:5]

        # الروشتات المحفوظة كـ draft
        drafted_prescriptions = Prescription.objects.filter(
            doctor__user=request.user,
            status='draft'
        )

        # حدّث الـ context
        context.update({
            'todays_appointments': todays_appointments,
            'next_queue_number': next_queue_number,
            'recent_patients': recent_patients,
            'drafted_prescriptions': drafted_prescriptions,
        })

    return render(request, 'home/home.html', context)
