# patient/urls.py

from django.urls import path
from . import views

app_name = 'patients'

urlpatterns = [
    path('new/', views.create_patient, name='create_patient'),       # ✅ تم التعديل هنا
    path('list/', views.patient_list, name='list'),
    path('<int:pk>/', views.patient_detail, name='detail'),
    path('<int:pk>/edit/', views.edit_patient, name='edit'),
    path('dashboard/', views.patient_dashboard, name='dashboard'),
]
