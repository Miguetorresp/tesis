import numpy as np
import faiss
from django.db.models import Q
from ..models import PetFaceDescriptor, Pet
from ..utils.face_descriptor import compare_descriptors
import logging

logger = logging.getLogger(__name__)


class PetMatcher:
    """
    Sistema optimizado de cotejamiento de mascotas perdidas
    usando FAISS para búsqueda vectorial rápida
    """

    def __init__(self):
        self.index = None
        self.descriptor_ids = []
        self.algorithm = 'resnet50'  # Algoritmo principal

    def build_index(self, algorithm='resnet50'):
        """
        Construir índice FAISS con todos los descriptores existentes
        """
        self.algorithm = algorithm

        # Obtener todos los descriptores del algoritmo especificado
        descriptors_qs = PetFaceDescriptor.objects.filter(
            algorithm=algorithm,
            pet__is_lost_report=True  # Solo mascotas reportadas como perdidas
        ).select_related('pet')

        if not descriptors_qs.exists():
            logger.warning(f"No hay descriptores {algorithm} para indexar")
            return None

        # Extraer vectores y IDs
        vectors = []
        ids = []

        for desc in descriptors_qs:
            vector = np.array(desc.descriptor, dtype='float32')
            vectors.append(vector)
            ids.append(desc.id)

        vectors_array = np.array(vectors)
        dimension = vectors_array.shape[1]

        # Crear índice FAISS (L2 distance)
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(vectors_array)
        self.descriptor_ids = ids

        logger.info(f"Índice FAISS construido: {len(ids)} descriptores, {dimension}D")
        return self.index

    def add_to_index(self, descriptor_obj):
        """
        Agregar un descriptor al índice existente (actualización incremental)

        Args:
            descriptor_obj: Instancia de PetFaceDescriptor
        """
        if self.index is None:
            logger.warning("Índice no existe, construyendo desde cero...")
            return self.build_index(self.algorithm)

        # Verificar que el algoritmo coincida
        if descriptor_obj.algorithm != self.algorithm:
            logger.warning(f"Descriptor usa {descriptor_obj.algorithm}, índice usa {self.algorithm}")
            return

        # Convertir descriptor a vector
        vector = np.array(descriptor_obj.descriptor, dtype='float32').reshape(1, -1)

        # Agregar al índice
        self.index.add(vector)
        self.descriptor_ids.append(descriptor_obj.id)

        logger.info(f"Descriptor {descriptor_obj.id} agregado al índice. Total: {len(self.descriptor_ids)}")
        return True

    def find_similar_pets(
            self,
            query_descriptor,
            threshold=80.0,
            top_k=10,
            filters=None
    ):
        """
        Buscar mascotas similares dado un descriptor

        Args:
            query_descriptor: Descriptor de la mascota a buscar (list o numpy array)
            threshold: Umbral de similitud mínimo (0-100)
            top_k: Número máximo de resultados
            filters: Dict con filtros adicionales (species, size, color, location)

        Returns:
            Lista de dicts con mascotas similares y su score
        """
        # Convertir descriptor a numpy array
        query_vector = np.array(query_descriptor, dtype='float32').reshape(1, -1)

        # Buscar en índice FAISS
        if self.index is None:
            self.build_index(self.algorithm)

        if self.index is None:
            return []

        # Buscar top_k vecinos más cercanos
        distances, indices = self.index.search(query_vector, min(top_k * 3, len(self.descriptor_ids)))

        # Convertir distancias a similitud (0-100)
        # FAISS retorna distancia L2, convertir a similitud
        similarities = self._distance_to_similarity(distances[0])

        results = []
        seen_pets = set()

        for idx, (descriptor_id, similarity) in enumerate(zip(indices[0], similarities)):
            if similarity < threshold:
                continue

            if descriptor_id >= len(self.descriptor_ids):
                continue

            db_descriptor_id = self.descriptor_ids[descriptor_id]

            try:
                descriptor_obj = PetFaceDescriptor.objects.select_related(
                    'pet', 'pet__species', 'pet__breed'
                ).get(id=db_descriptor_id)

                pet = descriptor_obj.pet

                # Evitar duplicados (misma mascota con múltiples descriptores)
                if pet.id in seen_pets:
                    continue

                # Aplicar filtros adicionales
                if filters and not self._apply_filters(pet, filters):
                    continue

                seen_pets.add(pet.id)

                results.append({
                    'pet_id': pet.id,
                    'pet': pet,
                    'similarity': round(similarity, 2),
                    'descriptor_id': descriptor_obj.id,
                    'algorithm': self.algorithm,
                    'match_details': {
                        'name': pet.name or 'Sin nombre',
                        'species': pet.species.name,
                        'breed': pet.breed.name if pet.breed else 'Desconocida',
                        'color': pet.color,
                        'location': pet.reported_location or 'No especificada',
                        'reported_at': pet.reported_at.isoformat() if pet.reported_at else None,
                        'reporter_name': pet.reporter_name or 'Anónimo',
                        'primary_image': pet.primary_image.image.url if pet.primary_image else None
                    }
                })

                # Limitar resultados finales
                if len(results) >= top_k:
                    break

            except PetFaceDescriptor.DoesNotExist:
                continue

        return sorted(results, key=lambda x: x['similarity'], reverse=True)

    def _distance_to_similarity(self, distances):
        """
        Convertir distancias L2 a porcentaje de similitud
        Normalización: e^(-distance/scale) * 100
        """
        # Escala ajustable según tus datos
        scale = 50.0
        similarities = np.exp(-distances / scale) * 100
        return similarities

    def _apply_filters(self, pet, filters):
        """
        Aplicar filtros adicionales a una mascota
        """
        if filters.get('species_id') and pet.species_id != filters['species_id']:
            return False

        if filters.get('size') and pet.size != filters['size']:
            return False

        # if filters.get('color'):
        #     # Búsqueda parcial en color
        #     if filters['color'].lower() not in pet.color.lower():
        #         return False

        # if filters.get('location_radius'):
        #     # Aquí podrías implementar búsqueda geográfica
        #     # Por ahora, búsqueda simple por texto
        #     if filters.get('location') and pet.reported_location:
        #         if filters['location'].lower() not in pet.reported_location.lower():
        #             return False

        return True

    def match_new_pet(self, pet, threshold=75.0, top_k=5, use_filters=True):
        """
        Buscar mascotas similares a una recién reportada

        Args:
            pet: Instancia de Pet recién creada
            threshold: Umbral de similitud mínimo
            top_k: Número de resultados
            use_filters: Si usar filtros de especie, tamaño, etc.

        Returns:
            Lista de mascotas similares
        """
        # Obtener descriptor principal de la mascota
        descriptor_obj = pet.face_descriptors.filter(algorithm=self.algorithm).first()

        if not descriptor_obj:
            logger.warning(f"Pet {pet.id} no tiene descriptor {self.algorithm}")
            return []

        # Preparar filtros
        filters = None
        if use_filters:
            filters = {
                'species_id': pet.species_id,
                'size': pet.size,
                'color': pet.color,
                'location': pet.reported_location
            }

        # Buscar similares
        results = self.find_similar_pets(
            descriptor_obj.descriptor,
            threshold=threshold,
            top_k=top_k,
            filters=filters
        )

        # Filtrar la misma mascota
        results = [r for r in results if r['pet_id'] != pet.id]

        return results


# Instancia global del matcher
_pet_matcher = None


def get_pet_matcher():
    """
    Obtener instancia singleton del matcher
    """
    global _pet_matcher
    if _pet_matcher is None:
        _pet_matcher = PetMatcher()
        _pet_matcher.build_index()
    return _pet_matcher


def rebuild_matcher_index():
    """
    Reconstruir índice (llamar cuando haya muchas mascotas nuevas)
    """
    global _pet_matcher
    _pet_matcher = PetMatcher()
    _pet_matcher.build_index()
    return _pet_matcher
