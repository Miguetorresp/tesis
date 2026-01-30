from tensorflow.keras.applications import ResNet50

model = ResNet50(weights="imagenet")
print("Modelo cargado correctamente")
