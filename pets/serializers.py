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

    class Meta:
        model = Pet
        fields = "__all__"
