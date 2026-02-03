from rest_framework import serializers
from .models import Pet, PetImage


class PetImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = PetImage
        fields = ['id', 'image', 'is_primary', 'caption']

    def get_image(self, obj):
        request = self.context.get('request')
        if request and obj.image:
            return request.build_absolute_uri(obj.image.url)
        return None


class PetSerializer(serializers.ModelSerializer):
    images = PetImageSerializer(many=True, read_only=True)

    species_name = serializers.CharField(source='species.name', read_only=True)
    breed_name = serializers.CharField(source='breed.name', read_only=True)
    sex_display = serializers.CharField(source='get_sex_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    size_display = serializers.CharField(source='get_size_display', read_only=True)
    health_status_display = serializers.CharField(
        source='get_health_status_display',
        read_only=True
    )

    class Meta:
        model = Pet
        fields = "__all__"
