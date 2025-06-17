# File: prescription/urls.py

from django.urls import path
from .views import (
    new_prescription,           # ← استورد الفيو الجديدة
    prescription_list,
    create_prescription,
    prescription_detail,
    edit_prescription,
    delete_prescription,
    download_pdf_prescription,
    send_prescription_whatsapp,
)

app_name = 'prescription'

urlpatterns = [
    # ➕ New Prescription: يوجّه تلقائياً للمريض التالي
    path('new/', new_prescription, name='new_prescription'),

    # 🗂️ List all prescriptions
    path('', prescription_list, name='list'),

    # ➕ Create a new prescription for a given appointment_id
    path('create/<int:appointment_id>/', create_prescription, name='create'),

    # 📄 View prescription detail
    path('<int:pk>/', prescription_detail, name='prescription_detail'),

    # ✏️ Edit
    path('<int:pk>/edit/', edit_prescription, name='edit'),

    # 🗑️ Delete
    path('<int:pk>/delete/', delete_prescription, name='delete'),

    # 📥 Download PDF
    path('<int:pk>/pdf/', download_pdf_prescription, name='download_pdf'),

    # 📤 WhatsApp
    path('<int:pk>/whatsapp/', send_prescription_whatsapp, name='send_whatsapp'),
]
