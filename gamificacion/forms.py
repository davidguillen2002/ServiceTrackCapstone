from django import forms
from ServiceTrack.models import Guia, ObservacionIncidente, Reto, Medalla


class GuiaForm(forms.ModelForm):
    class Meta:
        model = Guia
        fields = [
            'titulo', 'descripcion', 'categoria', 'manual', 'video',
            'tipo_servicio', 'equipo_marca', 'equipo_modelo', 'puntuacion'
        ]
        widgets = {
            'manual': forms.Textarea(attrs={'rows': 3}),
            'video': forms.TextInput(attrs={'placeholder': 'Enlace al video'}),
        }


class ObservacionIncidenteForm(forms.ModelForm):
    class Meta:
        model = ObservacionIncidente
        fields = [
            'autor', 'descripcion', 'tipo_observacion', 'comentarios',
            'estado', 'fecha_reportada', 'fecha_fin'
        ]

    def clean(self):
        cleaned_data = super().clean()
        fecha_reportada = cleaned_data.get("fecha_reportada")
        fecha_fin = cleaned_data.get("fecha_fin")

        if fecha_fin and fecha_fin < fecha_reportada:
            raise forms.ValidationError("La fecha de fin no puede ser anterior a la fecha reportada.")

        return cleaned_data


class RetoForm(forms.ModelForm):
    class Meta:
        model = Reto
        fields = ['nombre', 'descripcion', 'puntos_otorgados', 'criterio', 'valor_objetivo']
        labels = {
            'nombre': 'Nombre del reto',
            'descripcion': 'Descripción del reto',
            'puntos_otorgados': 'Puntos a otorgar',
            'criterio': 'Criterio de cumplimiento',
            'valor_objetivo': 'Valor objetivo (puntos, servicios, calificación promedio)',
        }

    def clean_puntos_otorgados(self):
        puntos = self.cleaned_data.get("puntos_otorgados")
        if puntos <= 0:
            raise forms.ValidationError("Los puntos otorgados deben ser mayores que cero.")
        return puntos

    def clean_valor_objetivo(self):
        valor_objetivo = self.cleaned_data.get("valor_objetivo")
        if valor_objetivo <= 0:
            raise forms.ValidationError("El valor objetivo debe ser mayor que cero.")
        return valor_objetivo


class MedallaForm(forms.ModelForm):
    class Meta:
        model = Medalla
        fields = ['nombre', 'descripcion', 'icono', 'puntos_necesarios']
        labels = {
            'nombre': 'Nombre de la medalla',
            'descripcion': 'Descripción',
            'icono': 'Ícono de la medalla',
            'puntos_necesarios': 'Puntos necesarios para desbloquear',
        }

    def clean_puntos_necesarios(self):
        puntos = self.cleaned_data.get("puntos_necesarios")
        if puntos <= 0:
            raise forms.ValidationError("Los puntos necesarios deben ser mayores que cero.")
        return puntos
