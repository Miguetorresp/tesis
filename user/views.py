from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from rest_framework_simplejwt.tokens import RefreshToken

from user.decorators import jwt_and_session_required
from .serializers import RegisterSerializer, LoginSerializer


# ------------------------------
#       REGISTRO API
# ------------------------------
class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Usuario creado correctamente"}, status=201)
        return Response(serializer.errors, status=400)


# ------------------------------
#       LOGIN API (JWT + SESIÓN + COOKIES)
# ------------------------------
class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        user = serializer.validated_data["user"]        # OBJETO REAL User
        user_data = serializer.validated_data["user_data"]  # DICCIONARIO SERIALIZADO

        # 1. Crear sesión Django
        login(request, user)

        # Guardar datos del usuario en la sesión
        request.session["user_data"] = {
            "user_id": user.user_id,
            "email": user.email,
            "first_name": user.first_name,
            "first_last_name": user.first_last_name,
            "role": user.groups.first().name if user.groups.exists() else None,
            "status": user.status,
            "full_name": f"{user.first_name} {user.first_last_name}".strip(),
            # "usuario": user
        }

        # 2. Crear tokens JWT
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        response = Response(
            {
                "message": "Login exitoso",
                "user": user_data,
            },
            status=200
        )

        # 3. Guardar JWT en cookies seguras HttpOnly
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,        # True si usas HTTPS (recomendado)
            samesite="Strict",
            max_age=60 * 30     # 30 minutos
        )

        response.set_cookie(
            key="refresh_token",
            value=str(refresh),
            httponly=True,
            secure=True,
            samesite="Strict",
            max_age=60 * 60 * 24 * 7  # 7 días
        )

        

        return response


# ------------------------------
#       PERFIL API PROTEGIDO
# ------------------------------
class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "id": user.user_id,
            "email": user.email,
            "first_name": user.first_name,
            "first_last_name": user.first_last_name,
            "cellphone": user.cellphone
        })


# ------------------------------
#       LOGIN HTML
# ------------------------------
def login_page(request):
    return render(request, "user/login.html")


# ------------------------------
#       DASHBOARD PROTEGIDO
# ------------------------------
@jwt_and_session_required
def dashboard(request):
    user_data = request.session.get("user_data")   # <--- YA FUNCIONA

    print("Datos enviados al template:", user_data)

    return render(request, "user/dashboard.html", {
        "user": user_data
    })

# Logout
def logout_view(request):
    response = redirect('login_page')

    # Eliminar cookies de tokens
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')
    response.delete_cookie('csrftoken')

    # Eliminar sesión de Django
    request.session.flush()

    return response