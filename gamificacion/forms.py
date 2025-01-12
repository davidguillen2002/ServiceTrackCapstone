from django import forms
from ServiceTrack.models import Guia, ObservacionIncidente, Reto, Medalla, Temporada, Recompensa


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

class TemporadaForm(forms.ModelForm):
    class Meta:
        model = Temporada
        fields = ['nombre', 'fecha_inicio', 'fecha_fin', 'activa']

class RecompensaForm(forms.ModelForm):
    class Meta:
        model = Recompensa
        fields = [
            'tipo', 'puntos_necesarios', 'descripcion', 'valor', 'reto', 'usuario', 'redimido'
        ]
        labels = {
            'tipo': 'Tipo de recompensa',
            'puntos_necesarios': 'Puntos necesarios para redimir',
            'descripcion': 'Descripción de la recompensa',
            'valor': 'Valor de la recompensa (monetario u otro)',
            'reto': 'Reto asociado',
            'usuario': 'Usuario (opcional)',
            'redimido': 'Estado de redención',
        }
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_puntos_necesarios(self):
        puntos = self.cleaned_data.get("puntos_necesarios")
        if puntos <= 0:
            raise forms.ValidationError("Los puntos necesarios deben ser mayores que cero.")
        return puntos

    def clean_valor(self):
        valor = self.cleaned_data.get("valor")
        if valor < 0:
            raise forms.ValidationError("El valor de la recompensa no puede ser negativo.")
        return valor

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get("tipo")
        descripcion = cleaned_data.get("descripcion")

        if not tipo or not descripcion:
            raise forms.ValidationError("El tipo y la descripción de la recompensa son obligatorios.")

        return cleaned_data