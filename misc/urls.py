# misc/urls.py
from django.urls import path

from . import views

urlpatterns = [
    path('rate', views.usd_rub_rate, name='usd_rub_rate'),
]
