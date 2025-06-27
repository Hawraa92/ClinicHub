from django.urls import path
from . import views

app_name = 'appointments'

urlpatterns = [
    # ==================== Secretary Interface ====================
    path(
        'secretary/',
        views.secretary_dashboard,
        name='secretary_dashboard'
    ),
    path(
        'secretary/new/',
        views.create_appointment,
        name='create_appointment'
    ),
    path(
        'secretary/edit/<int:pk>/',
        views.edit_appointment,
        name='edit_appointment'
    ),
    path(
        'secretary/delete/<int:pk>/',
        views.delete_appointment,
        name='delete_appointment'
    ),
    path(
        'secretary/list/',
        views.appointment_list,
        name='appointment_list'  # renamed from 'list'
    ),
    path(
        'secretary/settings/',
        views.secretary_settings,
        name='secretary_settings'
    ),

    # ==================== Public Booking =========================
    path(
        'book/',
        views.book_appointment_public,
        name='patient_book'
    ),
    path(
        'book/success/',
        views.book_success,
        name='book_success'
    ),

    # ==================== Queue Display & APIs ===================
    path(
        'queue/',
        views.queue_display,
        name='queue_display'
    ),
    path(
        'api/queue-number/',
        views.queue_number_api,
        name='queue_number_api'
    ),
    path(
        'api/call-next/<int:doctor_id>/',
        views.call_next_api,
        name='call_next_api'
    ),
    path(
        'api/current-patient/',
        views.current_patient_api,
        name='current_patient_api'
    ),

    # ==================== Ticket Print ===========================
    path(
        'ticket/<int:pk>/',
        views.appointment_ticket,
        name='appointment_ticket'
    ),

    path(
        'api/new-booking-requests/',
        views.new_booking_requests_api,
        name='new_booking_requests_api'
    ),
]
