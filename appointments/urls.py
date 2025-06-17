from django.urls import path
from . import views

app_name = 'appointments'

urlpatterns = [
    # 📅 Core Appointment Actions
    path('new/',                  views.create_appointment,    name='create_appointment'),
    path('edit/<int:pk>/',       views.edit_appointment,      name='edit_appointment'),
    path('delete/<int:pk>/',     views.delete_appointment,    name='delete_appointment'),

    # 👩‍💼 Secretary Interface
    path('secretary/',           views.secretary_dashboard,   name='secretary_dashboard'),
    path('list/',                views.appointment_list,      name='list'),
    path('settings/',            views.secretary_settings,    name='secretary_settings'),

    # 🖨️ Ticket Print (Cashier-style)
    path('ticket/<int:pk>/', views.appointment_ticket, name='appointment_ticket'),

    # 🛜 Public Queue Display + APIs
    path('queue/',                      views.queue_display,          name='queue'),
    path('api/queue-number/',           views.queue_number_api,       name='queue_number_api'),
    path('api/call-next/<int:doctor_id>/', views.call_next_api,      name='call_next_api'),
    path('api/current-patient/',        views.current_patient_api,   name='current_patient_api'),
]
