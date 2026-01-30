# utils/face_descriptor.py
import cv2
import numpy as np
import torch
import torchvision.transforms as transforms
from torchvision import models
from PIL import Image
import tensorflow as tf
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.applications.resnet50 import preprocess_input as resnet_preprocess
import os

# Configuración de modelos (se cargan una sola vez)
_MODELS_LOADED = False
_RESNET_MODEL = None
_YOLO_MODEL = None
_SIFT_DETECTOR = None
_ORB_DETECTOR = None


def _load_models():
    """
    Cargar modelos una sola vez (lazy loading)
    """
    global _MODELS_LOADED, _RESNET_MODEL, _YOLO_MODEL, _SIFT_DETECTOR, _ORB_DETECTOR

    if _MODELS_LOADED:
        return

    try:
        # ResNet50 para embeddings
        _RESNET_MODEL = ResNet50(
            weights='imagenet',
            include_top=False,
            pooling='avg',
            input_shape=(224, 224, 3)
        )
        print("✓ ResNet50 cargado")
    except Exception as e:
        print(f"✗ Error cargando ResNet50: {e}")

    try:
        # YOLOv5 para detección de mascotas
        _YOLO_MODEL = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
        _YOLO_MODEL.conf = 0.3  # Umbral de confianza
        print("✓ YOLOv5 cargado")
    except Exception as e:
        print(f"✗ Error cargando YOLOv5: {e}")
        _YOLO_MODEL = None

    # Detectores OpenCV
    _SIFT_DETECTOR = cv2.SIFT_create(nfeatures=100)
    _ORB_DETECTOR = cv2.ORB_create(nfeatures=500)

    _MODELS_LOADED = True


def detect_and_crop_pet(image_path):
    """
    Detectar la mascota en la imagen y retornar región de interés (ROI)
    Retorna: (cropped_image, animal_type, confidence, bbox)
    """
    _load_models()

    img = cv2.imread(image_path)
    if img is None:
        return None, 'unknown', 0.0, None

    # Intentar detectar con YOLO
    if _YOLO_MODEL is not None:
        try:
            results = _YOLO_MODEL(image_path)
            detections = results.pandas().xyxy[0]

            # Clases de animales en COCO dataset
            animal_classes = ['dog', 'cat', 'bird', 'horse', 'sheep', 'cow']
            pets = detections[detections['name'].isin(animal_classes)]

            if len(pets) > 0:
                # Tomar la detección con mayor confianza
                best_detection = pets.iloc[0]
                x1, y1, x2, y2 = (
                    int(best_detection['xmin']),
                    int(best_detection['ymin']),
                    int(best_detection['xmax']),
                    int(best_detection['ymax'])
                )

                # Expandir bbox un 10% para capturar más contexto
                h, w = img.shape[:2]
                margin_x = int((x2 - x1) * 0.1)
                margin_y = int((y2 - y1) * 0.1)

                x1 = max(0, x1 - margin_x)
                y1 = max(0, y1 - margin_y)
                x2 = min(w, x2 + margin_x)
                y2 = min(h, y2 + margin_y)

                cropped = img[y1:y2, x1:x2]
                animal_type = best_detection['name']
                confidence = float(best_detection['confidence'])
                bbox = (x1, y1, x2, y2)

                return cropped, animal_type, confidence, bbox
        except Exception as e:
            print(f"Error en detección YOLO: {e}")

    # Fallback: usar imagen completa
    return img, 'unknown', 0.0, None


def extract_resnet_embedding(image_path):
    """
    Extraer embedding usando ResNet50 (2048 dimensiones)
    """
    _load_models()

    if _RESNET_MODEL is None:
        return None

    cropped_img, animal_type, confidence, bbox = detect_and_crop_pet(image_path)

    if cropped_img is None:
        return None

    try:
        # Preprocesar imagen
        img_rgb = cv2.cvtColor(cropped_img, cv2.COLOR_BGR2RGB)
        img_resized = cv2.resize(img_rgb, (224, 224))
        img_array = np.expand_dims(img_resized, axis=0)
        img_preprocessed = resnet_preprocess(img_array)

        # Extraer embedding
        embedding = _RESNET_MODEL.predict(img_preprocessed, verbose=0)[0]

        return {
            'algorithm': 'resnet50',
            'descriptor': embedding.tolist(),
            'confidence': confidence,
            'animal_type': animal_type,
            'bbox': bbox
        }
    except Exception as e:
        print(f"Error extrayendo ResNet embedding: {e}")
        return None


def extract_sift_features(image_path):
    """
    Extraer características SIFT
    """
    _load_models()

    cropped_img, animal_type, confidence, bbox = detect_and_crop_pet(image_path)

    if cropped_img is None:
        return None

    try:
        gray = cv2.cvtColor(cropped_img, cv2.COLOR_BGR2GRAY)
        keypoints, descriptors = _SIFT_DETECTOR.detectAndCompute(gray, None)

        if descriptors is not None and len(descriptors) > 0:
            # Limitar a los primeros 100 keypoints más fuertes
            if len(keypoints) > 100:
                # Ordenar por response (fuerza del keypoint)
                sorted_indices = sorted(
                    range(len(keypoints)),
                    key=lambda i: keypoints[i].response,
                    reverse=True
                )[:100]
                keypoints = [keypoints[i] for i in sorted_indices]
                descriptors = descriptors[sorted_indices]

            # Calcular estadísticas como descriptor único (alternativa)
            # Esto permite usar el campo descriptor en vez de descriptor_json
            mean_desc = np.mean(descriptors, axis=0)
            std_desc = np.std(descriptors, axis=0)
            aggregated_desc = np.concatenate([mean_desc, std_desc])

            return {
                'algorithm': 'sift',
                'descriptor': aggregated_desc.tolist(),  # 256 dimensiones (128*2)
                'confidence': confidence,
                'animal_type': animal_type,
                'bbox': bbox,
                # Información adicional para matching preciso
                'keypoints_count': len(keypoints),
                'raw_descriptors': descriptors.tolist()[:50]  # Primeros 50 para matching
            }
    except Exception as e:
        print(f"Error extrayendo SIFT: {e}")

    return None


def extract_orb_features(image_path):
    """
    Extraer características ORB (más rápido que SIFT)
    """
    _load_models()

    cropped_img, animal_type, confidence, bbox = detect_and_crop_pet(image_path)

    if cropped_img is None:
        return None

    try:
        gray = cv2.cvtColor(cropped_img, cv2.COLOR_BGR2GRAY)
        keypoints, descriptors = _ORB_DETECTOR.detectAndCompute(gray, None)

        if descriptors is not None and len(descriptors) > 0:
            # ORB genera descriptores binarios de 32 bytes (256 bits)
            # Convertir a float para almacenar
            descriptors_float = descriptors.astype(np.float32)

            # Calcular estadísticas
            mean_desc = np.mean(descriptors_float, axis=0)
            std_desc = np.std(descriptors_float, axis=0)
            aggregated_desc = np.concatenate([mean_desc, std_desc])

            return {
                'algorithm': 'orb',
                'descriptor': aggregated_desc.tolist(),  # 64 dimensiones (32*2)
                'confidence': confidence,
                'animal_type': animal_type,
                'bbox': bbox,
                'keypoints_count': len(keypoints),
                'raw_descriptors': descriptors.tolist()[:100]  # Primeros 100
            }
    except Exception as e:
        print(f"Error extrayendo ORB: {e}")

    return None


def extract_face_descriptors_from_path(image_path):
    """
    Función principal que extrae el MEJOR descriptor de una imagen de mascota.

    Retorna: lista con UN SOLO dict (el más confiable):
    {
        'algorithm': str,
        'descriptor': [floats],
        'confidence': float,
        'animal_type': str,
        'bbox': tuple (opcional)
    }
    """
    img = cv2.imread(image_path)
    print(f'Procesando imagen: {image_path}')

    if img is None:
        print("✗ No se pudo cargar la imagen")
        return []

    all_descriptors = []

    # 1. Extraer ResNet embedding (PRINCIPAL - más confiable)
    print("Extrayendo ResNet50 embedding...")
    resnet_desc = extract_resnet_embedding(image_path)
    if resnet_desc:
        all_descriptors.append(resnet_desc)
        print(f"✓ ResNet50: {len(resnet_desc['descriptor'])} dimensiones, "
              f"animal detectado: {resnet_desc['animal_type']}, "
              f"confianza: {resnet_desc['confidence']:.2f}")

    # 2. Extraer SIFT features (para matching detallado)
    print("Extrayendo SIFT features...")
    sift_desc = extract_sift_features(image_path)
    if sift_desc:
        all_descriptors.append(sift_desc)
        print(f"✓ SIFT: {sift_desc['keypoints_count']} keypoints detectados, "
              f"confianza: {sift_desc['confidence']:.2f}")

    # 3. Extraer ORB features (rápido, complementario)
    print("Extrayendo ORB features...")
    orb_desc = extract_orb_features(image_path)
    if orb_desc:
        all_descriptors.append(orb_desc)
        print(f"✓ ORB: {orb_desc['keypoints_count']} keypoints detectados, "
              f"confianza: {orb_desc['confidence']:.2f}")

    if not all_descriptors:
        print("✗ No se pudieron extraer descriptores")
        return []

    # SELECCIONAR EL DESCRIPTOR MÁS CONFIABLE
    # Prioridad:
    # 1. ResNet50 (si confidence > 0.4)
    # 2. El de mayor confidence entre todos

    best_descriptor = None

    # Buscar ResNet50 primero
    resnet_descriptors = [d for d in all_descriptors if d['algorithm'] == 'resnet50']
    if resnet_descriptors and resnet_descriptors[0]['confidence'] >= 0.40:
        best_descriptor = resnet_descriptors[0]
        print(f"\n Descriptor seleccionado: ResNet50 (confianza: {best_descriptor['confidence']:.2%})")
    else:
        # Si ResNet no es confiable, tomar el de mayor confidence
        best_descriptor = max(all_descriptors, key=lambda x: x.get('confidence', 0))
        print(f"\n Descriptor seleccionado: {best_descriptor['algorithm']} "
              f"(confianza: {best_descriptor['confidence']:.2%})")

    # Retornar solo el mejor
    return [best_descriptor]


def compare_descriptors(desc1, desc2, algorithm):
    """
    Comparar dos descriptores según el algoritmo usado.
    Retorna: porcentaje de similitud (0-100)
    """
    if algorithm == 'resnet50':
        return _cosine_similarity(desc1, desc2)

    elif algorithm == 'sift':
        # Si tenemos raw_descriptors, hacer matching preciso
        # Si no, usar el descriptor agregado
        return _cosine_similarity(desc1, desc2)

    elif algorithm == 'orb':
        return _cosine_similarity(desc1, desc2)

    else:
        return 0.0


def _cosine_similarity(vec1, vec2):
    """
    Calcular similitud coseno entre dos vectores
    """
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)

    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    similarity = dot_product / (norm1 * norm2)
    # Convertir de [-1, 1] a [0, 100]
    return ((similarity + 1) / 2) * 100


def compare_pets(pet1_descriptors, pet2_descriptors):
    """
    Comparar dos conjuntos de descriptores de mascotas.

    Args:
        pet1_descriptors: QuerySet o lista de PetFaceDescriptor
        pet2_descriptors: QuerySet o lista de PetFaceDescriptor

    Returns:
        dict con similitudes por algoritmo y similitud total
    """
    similarities = {}

    # Agrupar descriptores por algoritmo
    pet1_by_algo = {}
    pet2_by_algo = {}

    for desc in pet1_descriptors:
        pet1_by_algo[desc.algorithm] = desc.descriptor

    for desc in pet2_descriptors:
        pet2_by_algo[desc.algorithm] = desc.descriptor

    # Comparar cada algoritmo
    for algo in pet1_by_algo:
        if algo in pet2_by_algo:
            similarity = compare_descriptors(
                pet1_by_algo[algo],
                pet2_by_algo[algo],
                algo
            )
            similarities[algo] = similarity

    # Calcular similitud ponderada
    weights = {
        'resnet50': 0.65,  # Mayor peso al embedding neuronal
        'sift': 0.20,
        'orb': 0.15
    }

    if similarities:
        total_weight = sum(weights.get(algo, 0.1) for algo in similarities)
        weighted_similarity = sum(
            similarities[algo] * weights.get(algo, 0.1)
            for algo in similarities
        ) / total_weight
    else:
        weighted_similarity = 0.0

    return {
        'similarities_by_algorithm': similarities,
        'total_similarity': round(weighted_similarity, 2)
    }
