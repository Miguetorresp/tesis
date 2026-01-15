from django.contrib import admin
from .models import Species, Breed, Pet, PetImage


@admin.register(Species)
class SpeciesAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']


@admin.register(Breed)
class BreedAdmin(admin.ModelAdmin):
    list_display = ['name', 'species', 'created_at']
    list_filter = ['species']
    search_fields = ['name', 'species__name']


class PetImageInline(admin.TabularInline):
    model = PetImage
    extra = 1
    fields = ['image', 'is_primary', 'caption']


@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = [
        'name', 
        'species', 
        'breed', 
        'age_display', 
        'sex', 
        'status', 
        'created_at'
    ]
    list_filter = [
        'status', 
        'species', 
        'sex', 
        'size', 
        'vaccinated', 
        'sterilized',
    ]
    search_fields = ['name', 'description', 'breed__name']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [PetImageInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': (
                'name', 
                'species', 
                'breed', 
                ('age_years', 'age_months'),
                'sex',
                'size',
                'color',
                'weight'
            )
        }),
        ('Descripción', {
            'fields': ('description',)
        }),
        ('Salud', {
            'fields': (
                'health_status',
                ('vaccinated', 'sterilized', 'dewormed', 'microchipped')
            )
        }),
        ('Compatibilidad', {
            'fields': (
                'good_with_kids',
                'good_with_dogs',
                'good_with_cats'
            )
        }),
        ('Estado y Metadata', {
            'fields': (
                'status',
                'created_by',
                'created_at',
                'updated_at'
            )
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Si es un nuevo objeto
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(PetImage)
class PetImageAdmin(admin.ModelAdmin):
    list_display = ['pet', 'is_primary', 'uploaded_at']
    list_filter = ['is_primary', 'uploaded_at']
    search_fields = ['pet__name', 'caption']
