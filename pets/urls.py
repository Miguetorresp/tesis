from django.urls import path
from . import views

app_name = 'pets'

urlpatterns = [
    path('', views.pet_list, name='list'),
    path('<int:pk>/', views.pet_detail, name='detail'),
    path('create/', views.pet_create, name='create'),
    path('<int:pk>/update/', views.pet_update, name='update'),
    path('<int:pk>/delete/', views.pet_delete, name='delete'),
    path('my-pets/', views.my_pets, name='my_pets'),
    path('api/breeds/<int:species_id>/', views.get_breeds_by_species, name='get_breeds'),
    path('lost/create/', views.create_lost_pet, name='lost_create'),
    path('lost/', views.lost_list, name='lost_list')  # crear vista de listado
]
