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
            'first_last_name', 'second_name', 'second_last_name', 'cellphone',
        ]

    def create(self, validated_data):
        user = User(
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            first_last_name=validated_data['first_last_name'],
            second_name=validated_data.get('second_name', None),
            second_last_name=validated_data.get('second_last_name', None),
            cellphone=validated_data.get('cellphone', None),
            role_id='2',  # Asignar rol por defecto
        )
        user.set_password(validated_data['password'])  # muy importante
        user.save()
        return user
    
class UserSerializer(serializers.ModelSerializer):
    # Si quieres añadir full_name:
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        # Asegúrate de que estos campos existan en tu modelo
        fields = ("user_id", "email", "first_name", "first_last_name", "role_id", "status", "full_name")

    def get_full_name(self, obj):
        # ajusta a los nombres reales de tus campos
        return f"{obj.first_name or ''} {obj.first_last_name or ''}".strip()

    

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

        # Serializar usuario
        user_data = UserSerializer(user).data

        # Retornar el objeto user REAL y también el diccionario serializado
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": user,           # <-- OBJETO REAL
            "user_data": user_data  # <-- SERIALIZADO
        }

