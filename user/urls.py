# from django.contrib import admin
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import RegisterView, LoginView, ProfileView, login_page

urlpatterns = [
    # Login HTML
    path('login/', login_page, name='login_page'),

    # Login API (POST JSON)
    path('auth/login/', LoginView.as_view(), name='api_login'),

    # Refresh token
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    path('register/', RegisterView.as_view(), name='register'),
    path('profile/', ProfileView.as_view(), name='profile'),

]
