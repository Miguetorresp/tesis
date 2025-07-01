from django.contrib import admin
from django.urls import path
from user import views

urlpatterns = [
    path('login/', views.Login),
    path('register/', views.Register),
]
