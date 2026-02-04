from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

User = get_user_model()


class Species(models.Model):
    """Especies de mascotas (Perro, Gato, etc.)"""
    name = models.CharField(max_length=50, unique=True, verbose_name='Especie')
    description = models.TextField(blank=True, verbose_name='Descripción')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Especie'
        verbose_name_plural = 'Especies'
        ordering = ['name']

    def __str__(self):
        return self.name


class Breed(models.Model):
    """Razas de mascotas"""
    species = models.ForeignKey(Species, on_delete=models.CASCADE, related_name='breeds', verbose_name='Especie')
    name = models.CharField(max_length=100, verbose_name='Raza')
    description = models.TextField(blank=True, verbose_name='Descripción')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Raza'
        verbose_name_plural = 'Razas'
        ordering = ['species', 'name']
        unique_together = ['species', 'name']

    def __str__(self):
        return f"{self.name}"


class Pet(models.Model):
    """Mascota disponible para adopción"""

    SIZE_CHOICES = [
        ('small', 'Pequeño (0-10 kg)'),
        ('medium', 'Mediano (11-25 kg)'),
        ('large', 'Grande (26-45 kg)'),
        ('xlarge', 'Extra Grande (45+ kg)'),
    ]

    SEX_CHOICES = [
        ('M', 'Macho'),
        ('F', 'Hembra'),
    ]

    STATUS_CHOICES = [
        ('available', 'Disponible'),
        ('pending', 'Adopción Pendiente'),
        ('adopted', 'Adoptado'),
        ('unavailable', 'No Disponible'),
        ('lost', 'Perdido'),
        ('found', 'Encontrado'),
    ]

    HEALTH_STATUS_CHOICES = [
        ('healthy', 'Saludable'),
        ('treatment', 'En Tratamiento'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, related_name='pets', verbose_name='Usuario')

    # Relaciones
    species = models.ForeignKey(Species, on_delete=models.PROTECT, related_name='pets', verbose_name='Especie')
    breed = models.ForeignKey(Breed, on_delete=models.SET_NULL, null=True, blank=True, related_name='pets',
                              verbose_name='Raza')

    # Información básica
    name = models.CharField(max_length=100, verbose_name='Nombre', null=True, blank=True)
    age_years = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(30)],
        verbose_name='Edad (años)',
        help_text='Edad aproximada en años',
        null=True,
        blank=True
    )
    age_months = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(11)],
        default=0,
        verbose_name='Meses adicionales',
        help_text='Meses adicionales (0-11)',
        null=True,
        blank=True
    )
    sex = models.CharField(max_length=1, choices=SEX_CHOICES, verbose_name='Sexo')
    size = models.CharField(max_length=10, choices=SIZE_CHOICES, verbose_name='Tamaño')
    color = models.CharField(max_length=100, verbose_name='Color')
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Peso (kg)'
    )

    # Descripción y características
    description = models.TextField(verbose_name='Descripción general')
    # personality = models.TextField(verbose_name='Personalidad', help_text='Temperamento y comportamiento')
    # special_needs = models.TextField(blank=True, verbose_name='Necesidades especiales')

    # Estado de salud
    health_status = models.CharField(
        max_length=20,
        choices=HEALTH_STATUS_CHOICES,
        default='healthy',
        verbose_name='Estado de salud'
    )
    vaccinated = models.BooleanField(default=False, verbose_name='Vacunado')
    sterilized = models.BooleanField(default=False, verbose_name='Esterilizado')
    dewormed = models.BooleanField(default=False, verbose_name='Desparasitado')
    microchipped = models.BooleanField(default=False, verbose_name='Con microchip')

    # Compatibilidad
    good_with_kids = models.BooleanField(default=True, verbose_name='Bueno con niños')
    good_with_dogs = models.BooleanField(default=True, verbose_name='Bueno con perros')
    good_with_cats = models.BooleanField(default=True, verbose_name='Bueno con gatos')

    # Estado y metadata
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='available',
        verbose_name='Estado'
    )
    # rescue_date = models.DateField(verbose_name='Fecha de rescate', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de registro')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última actualización')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='pets_created',
        verbose_name='Creado por'
    )

    is_lost_report = models.BooleanField(default=False, db_index=True)
    reported_at = models.DateTimeField(null=True, blank=True, auto_now_add=True, verbose_name='Fecha de reporte')
    reported_location = models.CharField(max_length=255, null=True, blank=True)
    reporter_name = models.CharField(max_length=100, null=True, blank=True)
    ubication_details = models.TextField(null=True, blank=True)

    # Featured
    # is_featured = models.BooleanField(default=False, verbose_name='Destacado')
    # views_count = models.IntegerField(default=0, verbose_name='Número de vistas')

    class Meta:
        verbose_name = 'Mascota'
        verbose_name_plural = 'Mascotas'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['species', 'status']),
        ]

    def __str__(self):
        return f"{self.name} - {self.species.name}"

    @property
    def age_display(self):
        """Retorna la edad en formato legible"""
        if self.age_years == 0:
            return f"{self.age_months} meses"
        elif self.age_months == 0:
            return f"{self.age_years} {'año' if self.age_years == 1 else 'años'}"
        else:
            return f"{self.age_years} {'año' if self.age_years == 1 else 'años'} y {self.age_months} {'mes' if self.age_months == 1 else 'meses'}"

    @property
    def primary_image(self):
        """Retorna la imagen principal"""
        return self.images.filter(is_primary=True).first() or self.images.first()

    def increment_views(self):
        """Incrementa el contador de vistas"""
        self.views_count += 1
        self.save(update_fields=['views_count'])


class PetImage(models.Model):
    """Imágenes de mascotas"""
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='images', verbose_name='Mascota')
    image = models.ImageField(upload_to='pets/%Y/%m/%d/', verbose_name='Imagen')
    is_primary = models.BooleanField(default=False, verbose_name='Imagen principal')
    caption = models.CharField(max_length=200, blank=True, verbose_name='Descripción')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de subida')

    class Meta:
        verbose_name = 'Imagen de Mascota'
        verbose_name_plural = 'Imágenes de Mascotas'
        ordering = ['-is_primary', 'uploaded_at']

    def __str__(self):
        return f"Imagen de {self.pet.name}"

    def save(self, *args, **kwargs):
        # Si esta imagen se marca como principal, desmarcar las demás
        if self.is_primary:
            PetImage.objects.filter(pet=self.pet, is_primary=True).update(is_primary=False)
        super().save(*args, **kwargs)


class PetFaceDescriptor(models.Model):
    ALGORITHM_CHOICES = [
        ('arcface', 'ArcFace Embedding'),
        ('resnet50', 'ResNet50 Embedding'),
        ('sift', 'SIFT Descriptors'),
        ('orb', 'ORB Descriptors'),
        ('yolo_face', 'YOLO Pet Face Detection'),
    ]
    pet = models.ForeignKey('Pet', related_name='face_descriptors', on_delete=models.CASCADE)
    pet_image = models.ForeignKey('PetImage', related_name='face_descriptors', on_delete=models.CASCADE)
    algorithm = models.CharField(max_length=50, choices=ALGORITHM_CHOICES)  # ej: "face_recognition+opencv"
    descriptor = models.JSONField()  # lista de floats (embeddings) - requiere Django >=3.1 o Postgres JSONField

    # Para descriptores clásicos (SIFT/ORB) que pueden ser muchos keypoints
    # Los guardamos como JSON si son múltiples vectores
    descriptor_json = models.JSONField(null=True, blank=True)

    confidence = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=['pet', 'algorithm']),
            models.Index(fields=['algorithm', 'created_at']),
        ]

    def __str__(self):
        return f"{self.algorithm} - Pet {self.pet_id} - Image {self.pet_image_id}"


class PetMatch(models.Model):
    """
    Registro de coincidencias entre mascotas perdidas/encontradas
    """
    STATUS_CHOICES = [
        ('pending', 'Pendiente de Revisión'),
        ('confirmed', 'Confirmado - Es la misma mascota'),
        ('rejected', 'Rechazado - No es la misma'),
        ('contacted', 'Usuario contactado'),
    ]

    # Mascota reportada como perdida
    lost_pet = models.ForeignKey(
        Pet,
        on_delete=models.CASCADE,
        related_name='potential_matches',
        verbose_name='Mascota Perdida'
    )

    # Mascota potencialmente coincidente
    found_pet = models.ForeignKey(
        Pet,
        on_delete=models.CASCADE,
        related_name='matched_as_found',
        verbose_name='Posible Coincidencia'
    )

    # Detalles del match
    similarity_score = models.FloatField(
        verbose_name='Porcentaje de Similitud',
        help_text='0-100, donde 100 es idéntico'
    )

    algorithm = models.CharField(
        max_length=50,
        verbose_name='Algoritmo Usado'
    )

    match_details = models.JSONField(
        default=dict,
        verbose_name='Detalles del Match',
        help_text='Información adicional sobre la coincidencia'
    )

    # Estado del match
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Estado'
    )

    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Detección'
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Revisión'
    )

    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_matches',
        verbose_name='Revisado por'
    )

    notes = models.TextField(
        blank=True,
        verbose_name='Notas'
    )

    class Meta:
        verbose_name = 'Coincidencia de Mascota'
        verbose_name_plural = 'Coincidencias de Mascotas'
        ordering = ['-similarity_score', '-created_at']
        unique_together = ['lost_pet', 'found_pet']
        indexes = [
            models.Index(fields=['lost_pet', 'status']),
            models.Index(fields=['similarity_score', '-created_at']),
        ]

    def __str__(self):
        return f"Match: {self.lost_pet.name} <-> {self.found_pet.name} ({self.similarity_score}%)"

    @property
    def is_high_confidence(self):
        """Match de alta confianza (>85%)"""
        return self.similarity_score >= 85

    @property
    def is_medium_confidence(self):
        """Match de confianza media (70-85%)"""
        return 70 <= self.similarity_score < 85
