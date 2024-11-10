# forms.py
from django import forms
from ServiceTrack.models import Servicio

class ServicioEstadoForm(forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ['estado']  # Solo el campo de estado

class ResenaForm(forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ['calificacion', 'comentario_cliente']
        labels = {
            'calificacion': 'Calificación (1-5)',
            'comentario_cliente': 'Comentario del Cliente'
        }
        widgets = {
            'calificacion': forms.NumberInput(attrs={'min': 1, 'max': 5}),
            'comentario_cliente': forms.Textarea(attrs={'rows': 3}),
        }