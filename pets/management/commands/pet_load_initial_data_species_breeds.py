from django.core.management.base import BaseCommand
from pets.models import Species, Breed


class Command(BaseCommand):
    help = 'Carga datos iniciales de especies y razas'

    def handle(self, *args, **kwargs):
        # Especies
        dog = Species.objects.get_or_create(name='Perro')[0]
        cat = Species.objects.get_or_create(name='Gato')[0]
        
        # Razas de perros
        dog_breeds = [
            'Mestizo', 'Labrador', 'Golden Retriever', 'Pastor Alemán',
            'Bulldog', 'Beagle', 'Poodle', 'Chihuahua', 'Husky Siberiano',
            'Dálmata', 'Boxer', 'Schnauzer', 'Cocker Spaniel'
        ]
        
        for breed_name in dog_breeds:
            Breed.objects.get_or_create(species=dog, name=breed_name)
        
        # Razas de gatos
        cat_breeds = [
            'Mestizo', 'Persa', 'Siamés', 'Maine Coon', 'Bengalí',
            'Ragdoll', 'British Shorthair', 'Sphynx', 'Angora'
        ]
        
        for breed_name in cat_breeds:
            Breed.objects.get_or_create(species=cat, name=breed_name)
        
        self.stdout.write(self.style.SUCCESS('Datos iniciales cargados exitosamente'))