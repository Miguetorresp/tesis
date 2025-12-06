# from django.contrib import admin
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import RegisterView, LoginView, ProfileView, dashboard, login_page, logout_view

urlpatterns = [
    # Login HTML
    path('login/', login_page, name='login_page'),

    # Login API (POST JSON)
    path('auth/login/', LoginView.as_view(), name='api_login'),

    path('auth/logout/', logout_view, name='api_logout'),

    # Refresh token
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    path('auth/register/', RegisterView.as_view(), name='api_register'),
    path('profile/', ProfileView.as_view(), name='profile'),

    path("dashboard/", dashboard, name="dashboard"),

]
