from django import forms
from .models import Pet, PetImage, Species, Breed


# 1. Crear el widget que acepta múltiples archivos
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


# 2. Crear el campo que usa ese widget
class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class PetForm(forms.ModelForm):
    # Usar el nuevo campo personalizado
    images = MultipleFileField(
        label='Imágenes',
        required=False,
        widget=MultipleFileInput(attrs={'class': 'form-control', 'multiple': True})
    )

    class Meta:
        model = Pet
        fields = [
            'name', 'species', 'breed', 'age_years', 'age_months',
            'sex', 'size', 'color', 'weight', 'description',
            'health_status', 'vaccinated', 'sterilized',
            'dewormed', 'microchipped', 'good_with_kids', 'good_with_dogs',
            'good_with_cats', 'ubication_details',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Agregar clases CSS a todos los campos
        for field_name, field in self.fields.items():
            if field_name != 'images':
                field.widget.attrs['class'] = 'form-control'

        # Filtrar razas dinámicamente
        if 'species' in self.data:
            try:
                species_id = int(self.data.get('species'))
                self.fields['breed'].queryset = Breed.objects.filter(species_id=species_id).order_by('name')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields['breed'].queryset = self.instance.species.breeds.order_by('name')


class PetSearchForm(forms.Form):
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Buscar por nombre...',
            'class': 'form-control'
        })
    )
    species = forms.ModelChoiceField(
        queryset=Species.objects.all(),
        required=False,
        empty_label='Todas las especies',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    sex = forms.ChoiceField(
        choices=[('', 'Todos')] + list(Pet.SEX_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    size = forms.ChoiceField(
        choices=[('', 'Todos los tamaños')] + list(Pet.SIZE_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    age_min = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'placeholder': 'Edad mínima',
            'class': 'form-control'
        })
    )
    age_max = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'placeholder': 'Edad máxima',
            'class': 'form-control'
        })
    )
    vaccinated = forms.BooleanField(required=False, label='Solo vacunados')
    sterilized = forms.BooleanField(required=False, label='Solo esterilizados')


class PetImageForm(forms.ModelForm):
    class Meta:
        model = PetImage
        fields = ['image', 'is_primary', 'caption']
        widgets = {
            'caption': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descripción de la imagen'}),
        }
