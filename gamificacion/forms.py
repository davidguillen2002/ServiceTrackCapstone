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
    temporada = forms.ModelChoiceField(
        queryset=Temporada.objects.all(),
        required=True,
        label="Temporada",
        help_text="Selecciona la temporada a la que pertenece este reto."
    )

    class Meta:
        model = Reto
        fields = ['nombre', 'descripcion', 'puntos_otorgados', 'criterio', 'valor_objetivo', 'temporada']
        labels = {
            'nombre': 'Nombre del reto',
            'descripcion': 'Descripción del reto',
            'puntos_otorgados': 'Puntos a otorgar',
            'criterio': 'Criterio de cumplimiento',
            'valor_objetivo': 'Valor objetivo (puntos, servicios, calificación promedio)',
            'temporada': 'Temporada asociada al reto',
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
    temporada = forms.ModelChoiceField(
        queryset=Temporada.objects.all(),
        required=False,  # Permitir que sea opcional
        label="Temporada",
        help_text="Selecciona la temporada a la que pertenece esta medalla (opcional)."
    )

    class Meta:
        model = Medalla
        fields = ['nombre', 'descripcion', 'icono', 'puntos_necesarios', 'nivel_requerido', 'temporada']
        labels = {
            'nombre': 'Nombre de la medalla',
            'descripcion': 'Descripción',
            'icono': 'Ícono de la medalla',
            'puntos_necesarios': 'Puntos necesarios para desbloquear',
            'nivel_requerido': 'Nivel mínimo requerido',
            'temporada': 'Temporada asociada a la medalla',
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
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get("fecha_inicio")
        fecha_fin = cleaned_data.get("fecha_fin")

        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            raise forms.ValidationError("La fecha de inicio no puede ser posterior a la fecha de fin.")

        return cleaned_data


class RecompensaForm(forms.ModelForm):
    temporada = forms.ModelChoiceField(
        queryset=Temporada.objects.all(),
        required=True,
        label="Temporada",
        help_text="Selecciona la temporada a la que pertenece esta recompensa."
    )

    class Meta:
        model = Recompensa
        fields = [
            'tipo', 'descripcion', 'valor', 'puntos_necesarios', 'temporada', 'reto'
        ]
        labels = {
            'tipo': 'Tipo de recompensa',
            'descripcion': 'Descripción de la recompensa',
            'valor': 'Valor de la recompensa (monetario u otro)',
            'puntos_necesarios': 'Puntos necesarios para redimir',
            'temporada': 'Temporada asociada a la recompensa',
            'reto': 'Reto asociado a la recompensa (opcional)',
        }
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Describe la recompensa en detalle.'}),
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
        if valor > 10000:
            raise forms.ValidationError("El valor de la recompensa parece ser demasiado alto.")
        return valor

    def clean(self):
        cleaned_data = super().clean()
        temporada = cleaned_data.get("temporada")
        reto = cleaned_data.get("reto")

        if reto and reto.temporada != temporada:
            raise forms.ValidationError("El reto asociado debe pertenecer a la misma temporada que la recompensa.")

        return cleaned_data
