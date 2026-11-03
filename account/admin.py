from django.contrib import admin

# Register your models here.
# account/urls_admin.py
from django.urls import path
from . import views



urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    # Add other admin-specific URLs here
]

