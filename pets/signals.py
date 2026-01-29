from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import PetImage, PetFaceDescriptor
from .utils.face_descriptor import extract_face_descriptors_from_path
import os


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

    descriptors = extract_face_descriptors_from_path(image_path)

    for d in descriptors:
        PetFaceDescriptor.objects.create(
            pet=pet,
            pet_image=instance,
            algorithm=d.get('algorithm', 'unknown'),
            descriptor=d.get('descriptor', []),
            confidence=d.get('confidence')
        )
