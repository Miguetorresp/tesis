from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'email', 'password', 'first_name',
            'first_last_name', 'cellphone',
        ]

    def create(self, validated_data):
        user = User(
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            first_last_name=validated_data['first_last_name'],
            cellphone=validated_data.get('cellphone', None)
        )
        user.set_password(validated_data['password'])  # muy importante
        user.save()
        return user
    
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        # Autenticar usando email y password
        user = authenticate(email=email, password=password)

        if not user:
            raise serializers.ValidationError("Credenciales inválidas")

        if not user.is_active:
            raise serializers.ValidationError("La cuenta está desactivada")

        # Generar tokens JWT
        refresh = RefreshToken.for_user(user)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "user_id": user.user_id,
                "email": user.email,
                "first_name": user.first_name,
                "first_last_name": user.first_last_name,
                "role": user.role_id,
                "status": user.status,
            }
        }


