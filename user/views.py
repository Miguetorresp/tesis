from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.

def Login(request):
    return HttpResponse("Hola, estas en el login")

def Register(request):
    return HttpResponse("Hola, estas en el registro")