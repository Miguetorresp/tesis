from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from .models import Pet, PetImage, Species, Breed, PetMatch
from .forms import PetForm, PetSearchForm, PetImageForm
from user.decorators import jwt_and_session_required
from django.http import JsonResponse
from .serializers import PetSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.core.exceptions import FieldDoesNotExist
from .utils.pet_matcher import get_pet_matcher, rebuild_matcher_index
import logging

logger = logging.getLogger(__name__)


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
        is_mine = (
                request.user.is_authenticated and
                pet.user == request.user
        )
        serializer = PetSerializer(pet, context={'request': request})
        return Response({
            "success": True,
            "message": "Mascota encontrada",
            "pet": serializer.data,
            "is_mine": is_mine
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
            pet = form.save(commit=False)
            # is_lost_report = request.POST.get('is_lost_report', 'false').lower() == 'true'
            # logger.info(f"Error reconstruyendo índice: ", form)
            status_pet = form.cleaned_data.get('status')
            if status_pet == 'lost':
                pet.is_lost_report = True
            pet.save()

            # Manejar nuevas imágenes
            images = request.FILES.getlist('images')
            if images:
                # 1️⃣ Eliminar imágenes anteriores (BD + archivos)
                for img in pet.images.all():
                    img.image.delete(save=False)  # elimina archivo físico
                    img.delete()  # elimina registro

                # 2️⃣ Guardar nuevas imágenes
                for idx, image in enumerate(images):
                    PetImage.objects.create(
                        pet=pet,
                        image=image,
                        is_primary=(idx == 0)
                    )

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
    pets = Pet.objects.filter(user=request.user).select_related('species', 'breed')
    # serializer = PetSerializer(pets, context={'request': request})
    # print(serializer.data)
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
    status_choices = Pet.STATUS_CHOICES_MY_PETS
    breeds = Breed.objects.all()
    context = {
        'pets': page_obj,
        'query': query,
        "user": user_data,
        "species": species,
        "sex_choices": sex_choices,
        "size_choices": size_choices,
        "health_choices": health_choices,
        "status_choices": status_choices,
        "breeds": breeds,
    }
    return render(request, 'pets/my_pets.html', context)


def get_breeds_by_species(request, species_id):
    """API para obtener razas por especie (para carga dinámica)"""
    breeds = Breed.objects.filter(species_id=species_id).values('id', 'name')
    return JsonResponse(list(breeds), safe=False)


def create_lost_pet(request):
    """Crear una nueva mascota vía AJAX/Fetch"""
    print('request', request)
    if request.method == 'POST':
        # Si envías FormData con 'name' y demás campos
        form = PetForm(request.POST, request.FILES)

        if form.is_valid():
            pet = form.save(commit=False)
            assign_user = request.POST.get('assign_user', 'false').lower() == 'true'
            is_lost_report = request.POST.get('is_lost_report', 'false').lower() == 'true'
            pet.is_lost_report = is_lost_report
            # if assign_user:
            #     pet.user = request.user
            print('pet', pet)
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
                'message': f'Mascota reportada con éxito.',
                'pet_id': pet.pk
            })

        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)

    # Si no es POST
    return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)


def lost_list(request):
    """Mascotas reportadas por el usuario actual si es is_lost_report true y created_by el usuario"""
    user_data = request.session.get("user_data")
    # Obtener el query de búsqueda
    query = request.GET.get('q', '')
    pets = Pet.objects.filter(created_by=request.user, is_lost_report=True).select_related('species', 'breed')

    for pet in pets:
        print('pet', pet)
        is_mine = (
                request.user.is_authenticated and
                pet.user == request.user
        )
        pet.is_mine = is_mine

    # serializer = PetSerializer(pets, context={'request': request})
    # print(serializer.data)
    # Filtrar por nombre si hay query
    if query:
        pets = pets.filter(name__icontains=query)
    # Paginación: máximo 10 por página
    paginator = Paginator(pets, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    species = Species.objects.all()
    sex_choices = Pet.SEX_CHOICES
    size_choices = Pet.SIZE_CHOICES
    health_choices = Pet.HEALTH_STATUS_CHOICES
    status_choices = Pet.STATUS_CHOICES
    breeds = Breed.objects.all()
    context = {
        'pets': page_obj,
        'query': query,
        "user": user_data,
        "species": species,
        "sex_choices": sex_choices,
        "size_choices": size_choices,
        "health_choices": health_choices,
        "status_choices": status_choices,
        "breeds": breeds,
    }
    return render(request, 'pets/lost_list.html', context)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def manual_pet_match(request, pet_id):
    """
    Endpoint para cotejar manualmente una mascota perdida

    POST /api/pets/{pet_id}/match/

    Body (opcional):
    {
        "threshold": 75.0,      # Umbral mínimo de similitud (default: 70)
        "top_k": 10,            # Número máximo de resultados (default: 10)
        "use_filters": true,    # Usar filtros de especie/tamaño (default: true)
        "rebuild_index": false  # Reconstruir índice antes de buscar (default: false)
    }

    Response:
    {
        "success": true,
        "pet_id": 123,
        "matches_found": 5,
        "matches": [
            {
                "pet_id": 456,
                "similarity": 87.5,
                "match_details": {...}
            }
        ]
    }
    """
    try:
        pet = Pet.objects.get(pk=pet_id)
    except Pet.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Mascota no encontrada'
        }, status=status.HTTP_404_NOT_FOUND)

    # Verificar permisos
    if pet.created_by != request.user and not request.user.is_staff:
        return Response({
            'success': False,
            'message': 'No tienes permiso para cotejar esta mascota'
        }, status=status.HTTP_403_FORBIDDEN)

    logger.info(f"Error reconstruyendo índice: ")
    # Verificar que sea reporte de pérdida
    if not pet.is_lost_report:
        return Response({
            'success': False,
            'message': 'Esta mascota no está reportada como perdida'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Parámetros
    threshold = float(request.data.get('threshold', 70.0))
    top_k = int(request.data.get('top_k', 10))
    use_filters = request.data.get('use_filters', True)
    rebuild_index = request.data.get('rebuild_index', False)

    # logger.info(f"Cotejamiento manual de Pet {pet_id} por usuario {request.user.id}")

    try:
        # Obtener o reconstruir matcher
        if rebuild_index:
            logger.info("Reconstruyendo índice FAISS...")
            matcher = rebuild_matcher_index()
        else:
            matcher = get_pet_matcher()

        # Buscar coincidencias
        similar_pets = matcher.match_new_pet(
            pet=pet,
            threshold=threshold,
            top_k=top_k,
            use_filters=use_filters
        )

        # Guardar matches en BD (actualizar o crear)
        saved_matches = []
        for match in similar_pets:
            pet_match, created = PetMatch.objects.update_or_create(
                lost_pet=pet,
                found_pet_id=match['pet_id'],
                defaults={
                    'similarity_score': match['similarity'],
                    'algorithm': match['algorithm'],
                    'status': 'pending',
                    'match_details': match['match_details']
                }
            )
            saved_matches.append({
                'id': pet_match.id,
                'pet_id': match['pet_id'],
                'similarity': match['similarity'],
                'algorithm': match['algorithm'],
                'match_details': match['match_details'],
                'created': created
            })

        logger.info(f"Cotejamiento completado: {len(similar_pets)} coincidencias")

        return Response({
            'success': True,
            'pet_id': pet.id,
            'matches_found': len(similar_pets),
            'matches': saved_matches,
            'search_params': {
                'threshold': threshold,
                'top_k': top_k,
                'use_filters': use_filters,
                'index_rebuilt': rebuild_index
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error en cotejamiento manual: {e}", exc_info=True)
        return Response({
            'success': False,
            'message': f'Error al buscar coincidencias: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
# @jwt_and_session_required
def get_pet_matches(request, pet_id):
    """
    Obtener todas las coincidencias guardadas de una mascota

    GET /api/pets/{pet_id}/matches/

    Query params:
    - status: pending|confirmed|rejected (opcional)
    - min_similarity: float (opcional)
    """
    try:
        pet = Pet.objects.get(pk=pet_id)
    except Pet.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Mascota no encontrada'
        }, status=status.HTTP_404_NOT_FOUND)

    # Verificar permisos
    # if pet.created_by != request.user and not request.user.is_staff:
    #     return Response({
    #         'success': False,
    #         'message': 'No tienes permiso para ver las coincidencias'
    #     }, status=status.HTTP_403_FORBIDDEN)

    # Filtros
    matches_qs = PetMatch.objects.filter(lost_pet=pet).select_related(
        'found_pet',
        'found_pet__species',
        'found_pet__breed'
    )

    if status_filter := request.GET.get('status'):
        matches_qs = matches_qs.filter(status=status_filter)

    if min_similarity := request.GET.get('min_similarity'):
        matches_qs = matches_qs.filter(similarity_score__gte=float(min_similarity))

    # Serializar resultados
    matches_data = []
    for match in matches_qs:
        # Preparar match_details con conversión de fechas
        match_details = match.match_details.copy() if match.match_details else {}

        # Convertir reported_at a string si no lo está ya
        if 'reported_at' in match_details and match_details['reported_at']:
            if isinstance(match_details['reported_at'], str):
                # Ya está como string, formatear para display
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(match_details['reported_at'].replace('Z', '+00:00'))
                    match_details['reported_at'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass  # Si falla, dejar como está

        # verificar si es mia esa mascota
        is_mine = (
                request.user.is_authenticated and
                pet.user == request.user
        )

        matches_data.append({
            'id': match.id,
            'found_pet': {
                'id': match.found_pet.id,
                'name': match.found_pet.name or 'Sin nombre',
                'species': match.found_pet.species.name,
                'breed': match.found_pet.breed.name if match.found_pet.breed else 'Desconocida',
                'color': match.found_pet.color,
                'size': match.found_pet.get_size_display(),
                'location': match.found_pet.ubication_details,
                'reported_at': match.found_pet.reported_at.isoformat() if match.found_pet.reported_at else None,
                'primary_image': match.found_pet.primary_image.image.url if match.found_pet.primary_image else None,
                'sex': match.found_pet.sex,
                'is_mine': is_mine,
            },
            'similarity_score': match.similarity_score,
            'algorithm': match.algorithm,
            'status': match.status,
            'is_high_confidence': match.is_high_confidence,
            'created_at': match.created_at.isoformat() if match.created_at else None,
            'match_details': match_details
        })

    return Response({
        'success': True,
        'pet_id': pet.id,
        'total_matches': len(matches_data),
        'matches': matches_data
    }, status=status.HTTP_200_OK)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_match_status(request, match_id):
    """
    Actualizar estado de una coincidencia

    PATCH /api/matches/{match_id}/

    Body:
    {
        "status": "confirmed"|"rejected"|"contacted",
        "notes": "Opcional: notas sobre la decisión"
    }
    """
    try:
        match = PetMatch.objects.get(pk=match_id)
    except PetMatch.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Coincidencia no encontrada'
        }, status=status.HTTP_404_NOT_FOUND)

    # Verificar permisos
    if match.lost_pet.created_by != request.user and not request.user.is_staff:
        return Response({
            'success': False,
            'message': 'No tienes permiso para actualizar esta coincidencia'
        }, status=status.HTTP_403_FORBIDDEN)

    # Actualizar
    new_status = request.data.get('status')
    if new_status and new_status in dict(PetMatch.STATUS_CHOICES):
        match.status = new_status

    # Actualizar mascota Pet cunado el estado es confirmed
    if new_status == 'confirmed':
        lost_pet = match.lost_pet
        lost_pet.status = 'found'  # o el valor correcto según tus STATUS_CHOICES
        lost_pet.is_lost_report = False  # opcional, si ya no debe figurar como perdida
        lost_pet.save()

    # if notes := request.data.get('notes'):
    #     match.notes = notes

    from django.utils import timezone
    match.reviewed_at = timezone.now()
    match.reviewed_by = request.user
    match.save()

    return Response({
        'success': True,
        'match_id': match.id,
        'new_status': match.status
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rebuild_search_index(request):
    """
    Reconstruir el índice de búsqueda FAISS
    (Solo administradores)

    POST /api/admin/rebuild-index/
    """
    if not request.user.is_staff:
        return Response({
            'success': False,
            'message': 'Solo administradores pueden reconstruir el índice'
        }, status=status.HTTP_403_FORBIDDEN)

    try:
        logger.info(f"Reconstruyendo índice por usuario {request.user.id}")
        matcher = rebuild_matcher_index()

        total_descriptors = len(matcher.descriptor_ids) if matcher.descriptor_ids else 0

        return Response({
            'success': True,
            'message': 'Índice reconstruido exitosamente',
            'total_descriptors': total_descriptors
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error reconstruyendo índice: {e}", exc_info=True)
        return Response({
            'success': False,
            'message': f'Error al reconstruir índice: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@login_required
def pet_matches_view(request, pet_id):
    """
    Vista para mostrar las coincidencias de una mascota perdida

    GET /pets/{pet_id}/matches/
    """
    pet = get_object_or_404(Pet, pk=pet_id)

    # Verificar permisos
    if pet.created_by != request.user and not request.user.is_staff:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("No tienes permiso para ver estas coincidencias")

    # Verificar que sea reporte de pérdida
    if not pet.is_lost_report:
        from django.contrib import messages
        messages.warning(request, "Esta mascota no está reportada como perdida")

    context = {
        'pet': pet
    }

    return render(request, 'pets/pet_matches_list.html', context)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_contact_notification(request, match_id):
    """
    Enviar notificación al dueño cuando alguien quiere contactarlo

    POST /pets/matches/{match_id}/contact/
    """
    try:
        match = PetMatch.objects.select_related(
            'lost_pet__created_by',
            'found_pet__created_by',
            'lost_pet__species',
            'found_pet__species',
            'lost_pet__user',
            'found_pet__user'
        ).get(pk=match_id)
        is_mine = (
                request.user.is_authenticated and
                match.lost_pet.user == request.user
        )
        logger.info(f"""
        Match ID: {match.id}
        Lost Pet: {match.lost_pet}
        Lost Pet Owner: {match.lost_pet.created_by}
        Lost Pet Species: {match.lost_pet.species}
        Found Pet: {match.found_pet}
        Found Pet Owner: {match.found_pet.created_by}
        Found Pet Species: {match.found_pet.species}
        User Id del solicitante: {match.lost_pet.user}
        other user: {match.found_pet.user}
        is_mine: {is_mine}
        """)
    except PetMatch.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Coincidencia no encontrada'
        }, status=status.HTTP_404_NOT_FOUND)

    # Verificar permisos (solo el dueño de lost_pet puede contactar)
    # if match.lost_pet.created_by != request.user and not request.user.is_staff:
    #     return Response({
    #         'success': False,
    #         'message': 'No tienes permiso para contactar'
    #     }, status=status.HTTP_403_FORBIDDEN)

    # El usuario a notificar es el dueño de found_pet
    # owner_to_notify = match.found_pet.created_by
    # requester = request.user
    #
    # if not owner_to_notify:
    #     return Response({
    #         'success': False,
    #         'message': 'No se puede contactar: el dueño no está registrado'
    #     }, status=status.HTTP_400_BAD_REQUEST)

    # Verificar si la mascota es mia o no

    # Enviar notificación por email
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        # Información del solicitante
        requester = request.user

        if is_mine:
            subject = f"Notificación: Posible dueño de la mascota reportada"
            e_mail = match.found_pet.created_by.email or "No proporcionado"
            # owner_to_notify = match.lost_pet.created_by
            requester_info = f"{requester.first_name} {requester.first_last_name}" if requester.first_last_name else requester.username
            requester_email = requester.email or "No proporcionado"
            requester_phone = getattr(requester, 'phone', 'No proporcionado')
            owner_to_notify = match.found_pet.created_by
            message = f"""
                Hola,
                
                La mascota que reportaste como perdida tiene una posible coincidencia con una mascota reportada como perdida. Aquí te dejo los detalles:
                
                INFORMACIÓN DE LA COINCIDENCIA:
                ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                • Mascota reportada como perdida: {match.lost_pet.name}
                • Especie: {match.lost_pet.species.name}
                • Color: {match.lost_pet.color}
                • Ubicación reportada: {match.lost_pet.reported_location or 'No especificada'}
                • Similitud: {match.similarity_score:.1f}%
                
                DATOS DE CONTACTO:
                ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                • Nombre: {requester_info}
                • Email: {requester_email}
                • Teléfono: {requester_phone}
                
                Por favor, contacta directamente con esta persona para verificar si se trata de su mascota.
                
                IMPORTANTE: Verifica siempre la identidad antes de compartir información personal.
                
                Puedes ver más detalles en tu panel:
                {settings.SITE_URL}/pets/{match.found_pet.id}/matches/
                
                ¡Tu ayuda puede traer de vuelta a su mascota con su dueño!
                
                Saludos,
                El equipo de PetFinder
                        """
        else:
            subject = f"Notificación: Alguien cree que esta mascota es suya"
            e_mail = match.found_pet.created_by.email or "No proporcionado"
            # owner_to_notify = match.lost_pet.created_by
            requester_info = f"{requester.first_name} {requester.first_last_name}" if requester.first_last_name else requester.username
            requester_email = requester.email or "No proporcionado"
            requester_phone = getattr(requester, 'cellphone', 'No proporcionado')
            message = f"""
                Hola,
                
                ¡Tenemos excelentes noticias! Alguien cree haber encontrado a tu mascota "{match.found_pet.name}". Aquí te dejo los detalles:
                
                INFORMACIÓN DE LA COINCIDENCIA:
                ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                • Mascota reportada como encontrada: {match.found_pet.name}
                • Especie: {match.found_pet.species.name}
                • Color: {match.found_pet.color}
                • Ubicación reportada: {match.found_pet.reported_location or 'No especificada'}
                • Similitud: {match.similarity_score:.1f}%
                
                DATOS DE CONTACTO:
                ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                • Nombre: {requester_info}
                • Email: {requester_email}
                • Teléfono: {requester_phone}
                
                Por favor, contacta directamente con esta persona para verificar si se trata de esta mascota.
                
                IMPORTANTE: Verifica siempre la identidad antes de compartir información personal.
                
                Puedes ver más detalles en tu panel:
                {settings.SITE_URL}/pets/{match.lost_pet.id}/matches/
                
                ¡Esperamos que encuentres a tu mascota pronto!
                
                Saludos,
                El equipo de PetFinder
                        """
        logger.info(f"""
                mensaje: {message}
                subject: {subject}
                e_mail: {e_mail}
                """)

        # Enviar email
        if e_mail != "No proporcionado":
            send_mail(
                subject=subject,
                message=message,
                # from_email=settings.DEFAULT_FROM_EMAIL,
                from_email='jordy.torres@uisek.edu.ec',
                recipient_list=[e_mail],
                fail_silently=False
            )
            return Response({
                'success': True,
                'message': 'Notificación enviada correctamente',
                'contact_info': {
                    'name': requester_info,
                    'email': requester_email
                }
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'message': 'El dueño no tiene email registrado'
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f"Error enviando notificación de contacto: {e}", exc_info=True)
        return Response({
            'success': False,
            'message': f'Error al enviar notificación: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
