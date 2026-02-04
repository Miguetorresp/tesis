from django.core.management.base import BaseCommand
from pets.models import Pet, PetImage, PetFaceDescriptor
from pets.utils.face_descriptor import extract_face_descriptors_from_path
import os


class Command(BaseCommand):
    help = 'Generar descriptores para mascotas perdidas existentes'

    def handle(self, *args, **options):
        lost_pets = Pet.objects.filter(is_lost_report=True)
        total = lost_pets.count()

        self.stdout.write(f"Procesando {total} mascotas perdidas...")

        for idx, pet in enumerate(lost_pets, 1):
            self.stdout.write(f"\n[{idx}/{total}] Procesando Pet {pet.id}: {pet.name}")

            # Verificar si ya tiene descriptores
            if pet.face_descriptors.exists():
                self.stdout.write(f"  ✓ Ya tiene descriptores")
                continue

            # Procesar cada imagen
            for image in pet.images.all():
                if not image.image or not os.path.exists(image.image.path):
                    continue

                self.stdout.write(f"  Procesando imagen {image.id}...")

                descriptors = extract_face_descriptors_from_path(image.image.path)

                for d in descriptors:
                    PetFaceDescriptor.objects.create(
                        pet=pet,
                        pet_image=image,
                        algorithm=d.get('algorithm'),
                        descriptor=d.get('descriptor'),
                        confidence=d.get('confidence')
                    )

                self.stdout.write(f"  ✓ Generados {len(descriptors)} descriptores")

        self.stdout.write(self.style.SUCCESS(f"\n¡Completado! {total} mascotas procesadas"))
