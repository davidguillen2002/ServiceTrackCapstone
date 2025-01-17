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
        widgets = {
            'calificacion': forms.HiddenInput(),
            'comentario_cliente': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Escribe tu comentario...'}),
        }

    def clean_calificacion(self):
        calificacion = self.cleaned_data.get('calificacion')
        if not (1 <= calificacion <= 5):
            raise forms.ValidationError("La calificación debe estar entre 1 y 5.")
        return calificacion

