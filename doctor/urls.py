# doctor/urls.py

from django.urls import path
from . import views

app_name = 'doctor'

urlpatterns = [
    # ✅ Doctor's main dashboard (metrics, recent archives)
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # ✅ Doctor's patient records (renamed to use 'patient_records.html')
    path('dashboard/records/', views.doctor_dashboard, name='records'),
]
