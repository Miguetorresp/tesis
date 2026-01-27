import cv2
import face_recognition
import numpy as np

# Ruta a un cascade local si prefieres Haarcascade
CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"


def extract_face_descriptors_from_path(image_path):
    """
    Detecta caras con OpenCV y devuelve embeddings usando face_recognition.
    Resultado: lista de dicts: { 'box': [top, right, bottom, left], 'descriptor': [floats], 'algorithm': 'face_recognition' }
    """
    img = cv2.imread(image_path)
    if img is None:
        return []

    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Detect faces con face_recognition (usa dlib) o con OpenCV Haar
    # Aquí usamos face_recognition para obtener boxes fiables:
    boxes = face_recognition.face_locations(rgb, model='hog')  # o 'cnn' si instalaste dlib con GPU

    descriptors = []
    if not boxes:
        # fallback: usar Haarcascade (menos preciso)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        cascade = cv2.CascadeClassifier(CASCADE_PATH)
        haar_faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
        for (x, y, w, h) in haar_faces:
            top, right, bottom, left = y, x + w, y + h, x
            boxes.append((top, right, bottom, left))

    if boxes:
        encodings = face_recognition.face_encodings(rgb, boxes)
        for i, enc in enumerate(encodings):
            descriptors.append({
                'box': boxes[i],
                'descriptor': enc.tolist(),
                'algorithm': 'face_recognition+opencv',
                'confidence': None  # la librería da el embedding; confianza se puede calcular en comparación
            })

    return descriptors
