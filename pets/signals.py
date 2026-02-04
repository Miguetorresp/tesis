from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import PetImage, PetFaceDescriptor, Pet, PetMatch
from .utils.face_descriptor import extract_face_descriptors_from_path
from .utils.pet_matcher import get_pet_matcher
import os
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=PetImage)
def generate_face_descriptors(sender, instance, created, **kwargs):
    """
    Cuando se guarda una PetImage, si la mascota está marcada como perdida,
    extrae descriptores y los guarda en PetFaceDescriptor.
    """
    try:
        pet = instance.pet
    except Exception:
        return

    if not pet.is_lost_report:
        return

    # ruta absoluta del archivo
    if not instance.image:
        return

    image_path = instance.image.path
    if not os.path.exists(image_path):
        return

    logger.info(f"Extrayendo descriptores para Pet {pet.id}, imagen {instance.id}")

    descriptors = extract_face_descriptors_from_path(image_path)

    for d in descriptors:
        PetFaceDescriptor.objects.create(
            pet=pet,
            pet_image=instance,
            algorithm=d.get('algorithm', 'unknown'),
            descriptor=d.get('descriptor', []),
            confidence=d.get('confidence')
        )

    logger.info(f"Descriptores guardados: {len(descriptors)}")


@receiver(post_save, sender=PetFaceDescriptor)
def match_lost_pet_on_descriptor_save(sender, instance, created, **kwargs):
    """
    Cuando se crea un nuevo descriptor, buscar automáticamente
    mascotas similares y guardar los matches
    """
    if not created:
        return  # Solo procesar descriptores nuevos

    pet = instance.pet

    if not pet.is_lost_report:
        return  # Solo procesar reportes de pérdida

    logger.info(f"Buscando coincidencias para Pet {pet.id}")

    try:
        # Obtener matcher y agregar el nuevo descriptor al índice
        from .utils.pet_matcher import get_pet_matcher
        matcher = get_pet_matcher()

        # Verificar cuántos descriptores hay en el índice ANTES de agregar
        descriptors_before = len(matcher.descriptor_ids) if matcher.descriptor_ids else 0
        logger.info(f"Descriptores en índice ANTES: {descriptors_before}")

        # Agregar el descriptor al índice (actualización incremental)
        if instance.algorithm == matcher.algorithm:
            matcher.add_to_index(instance)
            logger.info(f"Descriptor {instance.id} agregado al índice")
            logger.info(f"Descriptores en índice AHORA: {len(matcher.descriptor_ids)}")

        # Buscar mascotas similares (umbral más bajo para pruebas)
        # NOTA: Umbral de 60% para detectar más coincidencias
        # Desactivar filtros inicialmente para ver si hay alguna coincidencia
        similar_pets = matcher.match_new_pet(
            pet=pet,
            threshold=60.0,  # Bajado de 70% a 60%
            top_k=20,  # Aumentado para ver más resultados
            use_filters=False  # Desactivado temporalmente para testing
        )

        logger.info(f"Encontradas {len(similar_pets)} coincidencias para Pet {pet.id}")

        # Log de las primeras 3 coincidencias
        for idx, match in enumerate(similar_pets[:3], 1):
            logger.info(f"  Match {idx}: Pet {match['pet_id']} con {match['similarity']:.1f}% similitud")

        # Guardar matches en la base de dato
        for match in similar_pets:
            PetMatch.objects.update_or_create(
                lost_pet=pet,
                found_pet_id=match['pet_id'],
                defaults={
                    'similarity_score': match['similarity'],
                    'algorithm': match['algorithm'],
                    'status': 'pending',
                    'match_details': match['match_details']
                }
            )

        # Si hay matches con alta similitud (>85%), notificar
        high_matches = [m for m in similar_pets if m['similarity'] >= 85]
        if high_matches:
            logger.warning(f"Pet {pet.id} tiene {len(high_matches)} coincidencias ALTAS (>85%)")
            # Aquí puedes enviar email/notificación al usuario
            # send_match_notification(pet, high_matches)

    except Exception as e:
        logger.error(f"Error buscando coincidencias para Pet {pet.id}: {e}")
