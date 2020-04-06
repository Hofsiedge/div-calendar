# payment/urls.py
from django.urls import path

from . import views

urlpatterns = [
    path('payments', views.get_payments, name='payments'),
]
