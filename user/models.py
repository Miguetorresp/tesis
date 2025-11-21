from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager,
)
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('status', 'active')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    user_id = models.BigAutoField(primary_key=True)
    first_name = models.CharField(max_length=150)
    second_name = models.CharField(max_length=150, null=True, blank=True)
    first_last_name = models.CharField(max_length=150, null=True, blank=True)
    second_last_name = models.CharField(max_length=150, null=True, blank=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    cellphone = models.CharField(max_length=30, null=True, blank=True)
    direction = models.TextField(null=True, blank=True)
    role_id = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, default='active')

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'first_last_name']

    def __str__(self):
        return f"{self.first_name} {self.first_last_name} <{self.email}>"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    photo = models.ImageField(null=True, blank=True)