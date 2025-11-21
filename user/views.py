# from django.shortcuts import render, redirect
# from django.http import HttpResponse
# from django.contrib.auth import authenticate, login
# from django.contrib import messages

# def Login(request):
#     if request.method == 'POST':
#         username = request.POST.get('username')
#         password = request.POST.get('password')
#         user = authenticate(request, username=username, password=password)
#         if user is not None:
#             login(request, user)
#             return redirect('/')  # cambiar destino si se desea
#         messages.error(request, 'Credenciales inválidas')
#     return render(request, 'user/login.html')

#     # return HttpResponse("Hola, estas en el login")

# def Register(request):
#     return HttpResponse("Hola, estas en el registro")

from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .serializers import RegisterSerializer, LoginSerializer
from .models import User

class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Usuario creado correctamente"}, status=201)
        return Response(serializer.errors, status=400)


class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=200)
        return Response(serializer.errors, status=400)


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
    
def login_page(request):
    return render(request, "user/login.html")