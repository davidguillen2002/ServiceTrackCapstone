from django import forms
from ServiceTrack.models import Guia, ObservacionIncidente, Reto, Medalla

class GuiaForm(forms.ModelForm):
    class Meta:
        model = Guia
        fields = [
            'titulo', 'descripcion', 'categoria', 'manual', 'video',
            'tipo_servicio', 'equipo_marca', 'equipo_modelo', 'puntuacion'
        ]

class ObservacionIncidenteForm(forms.ModelForm):
    class Meta:
        model = ObservacionIncidente
        fields = [
            'autor', 'descripcion', 'tipo_observacion', 'comentarios',
            'estado', 'fecha_reportada', 'fecha_fin'
        ]

class RetoForm(forms.ModelForm):
    class Meta:
        model = Reto
        fields = ['nombre', 'descripcion', 'puntos_otorgados', 'requisito']

class MedallaForm(forms.ModelForm):
    class Meta:
        model = Medalla
        fields = ['nombre', 'descripcion', 'icono', 'puntos_necesarios']