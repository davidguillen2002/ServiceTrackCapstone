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
        fields = ['nombre', 'descripcion', 'icono', 'puntos_necesarios', 'nivel_requerido']
        labels = {
            'nombre': 'Nombre de la medalla',
            'descripcion': 'Descripción',
            'icono': 'Ícono de la medalla',
            'puntos_necesarios': 'Puntos necesarios para desbloquear',
            'nivel_requerido': 'Nivel mínimo requerido',
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

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get("fecha_inicio")
        fecha_fin = cleaned_data.get("fecha_fin")

        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            raise forms.ValidationError("La fecha de inicio no puede ser posterior a la fecha de fin.")

        return cleaned_data


class RecompensaForm(forms.ModelForm):
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
        """
        Valida que los puntos necesarios sean mayores que cero.
        """
        puntos = self.cleaned_data.get("puntos_necesarios")
        if puntos <= 0:
            raise forms.ValidationError("Los puntos necesarios deben ser mayores que cero.")
        return puntos

    def clean_valor(self):
        """
        Valida que el valor de la recompensa sea positivo y razonable.
        """
        valor = self.cleaned_data.get("valor")
        if valor < 0:
            raise forms.ValidationError("El valor de la recompensa no puede ser negativo.")
        if valor > 10000:  # Límite arbitrario; ajusta según tus necesidades
            raise forms.ValidationError("El valor de la recompensa parece ser demasiado alto.")
        return valor

    def clean(self):
        """
        Validaciones generales del formulario.
        """
        cleaned_data = super().clean()
        tipo = cleaned_data.get("tipo")
        descripcion = cleaned_data.get("descripcion")
        temporada = cleaned_data.get("temporada")
        puntos_necesarios = cleaned_data.get("puntos_necesarios")
        reto = cleaned_data.get("reto")

        if not tipo or not descripcion or not temporada:
            raise forms.ValidationError("El tipo, la descripción y la temporada son obligatorios.")

        # Validación específica: si se proporciona un reto, debe coincidir con la temporada de la recompensa.
        if reto and reto.temporada != temporada:
            raise forms.ValidationError("El reto asociado debe pertenecer a la misma temporada que la recompensa.")

        # Validación adicional: verificar unicidad del reto si está presente.
        if reto:
            recompensa_existente = Recompensa.objects.filter(reto=reto).exclude(id=self.instance.id).first()
            if recompensa_existente:
                raise forms.ValidationError(
                    f"El reto '{reto.nombre}' ya está asociado a otra recompensa: '{recompensa_existente.descripcion}'."
                )

        return cleaned_data

