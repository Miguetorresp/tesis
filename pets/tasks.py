from celery import shared_task
from .models import Pet, PetMatch
from .utils.pet_matcher import get_pet_matcher
import logging

logger = logging.getLogger(__name__)


@shared_task
def match_lost_pet_async(pet_id, threshold=70.0, top_k=10):
    """
    Tarea asíncrona para buscar coincidencias de una mascota perdida

    Args:
        pet_id: ID de la mascota a cotejar
        threshold: Umbral de similitud
        top_k: Número máximo de resultados
    """
    try:
        pet = Pet.objects.get(pk=pet_id)

        if not pet.is_lost_report:
            logger.warning(f"Pet {pet_id} no es reporte de pérdida")
            return {'success': False, 'message': 'No es reporte de pérdida'}

        logger.info(f"[CELERY] Iniciando cotejamiento asíncrono para Pet {pet_id}")

        # Obtener matcher y buscar
        matcher = get_pet_matcher()
        similar_pets = matcher.match_new_pet(
            pet=pet,
            threshold=threshold,
            top_k=top_k,
            use_filters=True
        )

        # Guardar matches
        matches_created = 0
        for match in similar_pets:
            _, created = PetMatch.objects.update_or_create(
                lost_pet=pet,
                found_pet_id=match['pet_id'],
                defaults={
                    'similarity_score': match['similarity'],
                    'algorithm': match['algorithm'],
                    'status': 'pending',
                    'match_details': match['match_details']
                }
            )
            if created:
                matches_created += 1

        logger.info(f"[CELERY] Cotejamiento completado: {len(similar_pets)} matches, {matches_created} nuevos")

        # Enviar notificación si hay matches de alta confianza
        high_confidence = [m for m in similar_pets if m['similarity'] >= 85]
        if high_confidence and pet.user and pet.user.email:
            send_match_notification.delay(pet_id, high_confidence)

        return {
            'success': True,
            'pet_id': pet_id,
            'total_matches': len(similar_pets),
            'new_matches': matches_created,
            'high_confidence_count': len(high_confidence)
        }

    except Pet.DoesNotExist:
        logger.error(f"Pet {pet_id} no existe")
        return {'success': False, 'message': 'Mascota no encontrada'}

    except Exception as e:
        logger.error(f"Error en cotejamiento asíncrono de Pet {pet_id}: {e}", exc_info=True)
        return {'success': False, 'message': str(e)}


@shared_task
def send_match_notification(pet_id, matches):
    """
    Enviar notificación por email cuando se encuentran coincidencias

    Args:
        pet_id: ID de la mascota
        matches: Lista de coincidencias de alta confianza
    """
    try:
        from django.core.mail import send_mail
        from django.conf import settings

        pet = Pet.objects.get(pk=pet_id)

        if not pet.user or not pet.user.email:
            logger.warning(f"Pet {pet_id} no tiene usuario con email")
            return

        subject = f"🔔 Posibles coincidencias para {pet.name}"

        message = f"""
        Hola {pet.user.first_name or pet.user.username},

        ¡Tenemos buenas noticias! Se han encontrado {len(matches)} posibles coincidencias 
        de alta confianza para tu mascota perdida "{pet.name}".

        Detalles de las coincidencias:
        """

        for idx, match in enumerate(matches[:3], 1):  # Mostrar solo las 3 mejores
            message += f"""

        {idx}. Similitud: {match['similarity']:.1f}%
           - Especie: {match['match_details']['species']}
           - Color: {match['match_details']['color']}
           - Ubicación: {match['match_details']['location']}
           - Reportado: {match['match_details']['reported_at']}
        """

        message += f"""

        Por favor, revisa las coincidencias en tu panel de control:
        {settings.SITE_URL}/pets/{pet_id}/matches/

        ¡Esperamos que encuentres a tu mascota pronto!

        Saludos,
        El equipo de PetFinder
        """

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[pet.user.email],
            fail_silently=True
        )

        logger.info(f"Notificación enviada a {pet.user.email} para Pet {pet_id}")

    except Exception as e:
        logger.error(f"Error enviando notificación para Pet {pet_id}: {e}", exc_info=True)


@shared_task
def rebuild_matcher_index_async():
    """
    Reconstruir índice FAISS de forma asíncrona
    (programar para ejecutar diariamente)
    """
    try:
        from .utils.pet_matcher import rebuild_matcher_index

        logger.info("[CELERY] Reconstruyendo índice FAISS...")
        matcher = rebuild_matcher_index()

        total = len(matcher.descriptor_ids) if matcher.descriptor_ids else 0
        logger.info(f"[CELERY] Índice reconstruido: {total} descriptores")

        return {'success': True, 'total_descriptors': total}

    except Exception as e:
        logger.error(f"Error reconstruyendo índice: {e}", exc_info=True)
        return {'success': False, 'message': str(e)}
