from django import forms
from ServiceTrack.models import Servicio

class ServicioForm(forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ['equipo', 'tecnico', 'fecha_inicio', 'fecha_fin', 'estado', 'calificacion', 'comentario_cliente', 'costo']