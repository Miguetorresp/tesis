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
    path('lost/', views.lost_list, name='lost_list'),  # crear vista de listado

    # Endpoints de cotejamiento
    # path('api/pets/<int:pet_id>/match/', views.manual_pet_match, name='manual_pet_match'),
    # path('api/pets/<int:pet_id>/matches/', views.get_pet_matches, name='get_pet_matches'),
    # path('api/matches/<int:match_id>/', views.update_match_status, name='update_match_status'),

    # Admin
    # path('api/admin/rebuild-index/', views.rebuild_search_index, name='rebuild_search_index'),

    # Endpoints de cotejamiento
    path('<int:pet_id>/match/', views.manual_pet_match, name='manual_pet_match'),
    path('<int:pet_id>/matches/', views.get_pet_matches, name='get_pet_matches'),
    path('lost/<int:pet_id>/matches-list/', views.pet_matches_view, name='pet_matches_view'),
    path('matches/<int:match_id>/', views.update_match_status, name='update_match_status'),
    path('matches/<int:match_id>/contact/', views.send_contact_notification, name='send_contact_notification'),

    # Admin
    path('admin/rebuild-index/', views.rebuild_search_index, name='rebuild_search_index'),
]
