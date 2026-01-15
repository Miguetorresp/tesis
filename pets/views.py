from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Pet, PetImage, Species, Breed
from .forms import PetForm, PetSearchForm, PetImageForm
from user.decorators import jwt_and_session_required
from django.http import JsonResponse
from rest_framework.decorators import api_view
from .serializers import PetSerializer
from rest_framework.response import Response
from rest_framework import status


def pet_list(request):
    """Lista pública de mascotas disponibles para adopción"""
    pets = Pet.objects.filter(status='available').select_related('species', 'breed').prefetch_related('images')

    # Formulario de búsqueda y filtros
    form = PetSearchForm(request.GET)

    if form.is_valid():
        # Búsqueda por nombre
        if search := form.cleaned_data.get('search'):
            pets = pets.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(breed__name__icontains=search)
            )

        # Filtros
        if species := form.cleaned_data.get('species'):
            pets = pets.filter(species=species)

        if sex := form.cleaned_data.get('sex'):
            pets = pets.filter(sex=sex)

        if size := form.cleaned_data.get('size'):
            pets = pets.filter(size=size)

        if age_min := form.cleaned_data.get('age_min'):
            pets = pets.filter(age_years__gte=age_min)

        if age_max := form.cleaned_data.get('age_max'):
            pets = pets.filter(age_years__lte=age_max)

        if form.cleaned_data.get('vaccinated'):
            pets = pets.filter(vaccinated=True)

        if form.cleaned_data.get('sterilized'):
            pets = pets.filter(sterilized=True)

    # Paginación
    paginator = Paginator(pets, 12)  # 12 mascotas por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'form': form,
        'total_pets': pets.count()
    }
    return render(request, 'pets/list.html', context)


@api_view(['GET'])
def pet_detail(request, pk):
    try:
        pet = Pet.objects.get(pk=pk)
        serializer = PetSerializer(pet)
        return Response({
            "success": True,
            "message": "Mascota encontrada",
            "pet": serializer.data
        }, status=status.HTTP_200_OK)
    except Pet.DoesNotExist:
        return Response({
            "success": False,
            "message": "La mascota no existe"
        }, status=status.HTTP_404_NOT_FOUND)


def pet_create(request):
    """Crear una nueva mascota vía AJAX/Fetch"""
    if request.method == 'POST':
        # Si envías FormData con 'name' y demás campos
        form = PetForm(request.POST, request.FILES)

        if form.is_valid():
            pet = form.save(commit=False)
            assign_user = request.POST.get('assign_user', 'false').lower() == 'true'
            if assign_user:
                pet.user = request.user

            pet.created_by = request.user
            pet.save()

            # Guardar imágenes si las hay
            images = request.FILES.getlist('images')
            for idx, image in enumerate(images):
                PetImage.objects.create(
                    pet=pet,
                    image=image,
                    is_primary=(idx == 0)
                )

            # Retorna JSON para el fetch
            return JsonResponse({
                'success': True,
                # 'message': f'Mascota "{pet.name}" creada con éxito.',
                'message': f'Mascota creada con éxito.',
                'pet_id': pet.pk
            })

        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)

    # Si no es POST
    return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)


@jwt_and_session_required
def pet_update(request, pk):
    """Actualizar mascota existente vía AJAX"""
    pet = get_object_or_404(Pet, pk=pk)

    # Verificar permisos
    if pet.created_by != request.user and not request.user.is_staff:
        return JsonResponse({
            'success': False,
            'message': 'No tienes permiso para editar esta mascota.'
        }, status=403)

    if request.method == 'POST':
        form = PetForm(request.POST, request.FILES, instance=pet)
        if form.is_valid():
            pet = form.save()

            # Manejar nuevas imágenes
            images = request.FILES.getlist('images')
            for image in images:
                PetImage.objects.create(pet=pet, image=image)

            return JsonResponse({
                'success': True,
                'message': 'Mascota actualizada exitosamente',
                'pet_id': pet.pk
            })

        else:
            # Si hay errores de validación, devolverlos en JSON
            errors = form.errors.get_json_data()
            return JsonResponse({
                'success': False,
                'message': 'Hay errores en el formulario.',
                'errors': errors
            }, status=400)

    else:
        # Metodo no permitido
        return JsonResponse({
            'success': False,
            'message': 'Método no permitido.'
        }, status=405)


@jwt_and_session_required
def pet_delete(request, pk):
    """Eliminar mascota"""
    pet = get_object_or_404(Pet, pk=pk)

    # Verificar permisos
    if pet.created_by != request.user and not request.user.is_staff:
        return JsonResponse({
            'success': False,
            'message': 'No tienes permiso para eliminar esta mascota.',
            'pet_id': pet.pk
        }, status=403)

    if request.method == 'POST':
        pet.delete()
        return JsonResponse({
            'success': True,
            'message': f'Mascota eliminada',
            'pet_id': pk
        })

    # Si no es POST, retornar error
    return JsonResponse({
        'success': False,
        'message': 'Método no permitido.',
        'pet_id': pet.pk
    }, status=405)


@jwt_and_session_required
def my_pets(request):
    """Mascotas creadas por el usuario actual"""
    user_data = request.session.get("user_data")
    # Obtener el query de búsqueda
    query = request.GET.get('q', '')

    pets = Pet.objects.filter(user=request.user).select_related('species', 'breed').prefetch_related('images')

    # Filtrar por nombre si hay query
    if query:
        pets = pets.filter(name__icontains=query)
    # Paginación: máximo 10 por página
    paginator = Paginator(pets, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    species = Species.objects.all()
    sex_choices = Pet.SEX_CHOICES
    size_choices = Pet.SIZE_CHOICES
    health_choices = Pet.HEALTH_STATUS_CHOICES
    status_choices = Pet.STATUS_CHOICES

    context = {
        'pets': page_obj,
        'query': query,
        "user": user_data,
        "species": species,
        "sex_choices": sex_choices,
        "size_choices": size_choices,
        "health_choices": health_choices,
        "status_choices": status_choices,
    }

    return render(request, 'pets/my_pets.html', context)


def get_breeds_by_species(request, species_id):
    """API para obtener razas por especie (para carga dinámica)"""
    breeds = Breed.objects.filter(species_id=species_id).values('id', 'name')
    return JsonResponse(list(breeds), safe=False)
