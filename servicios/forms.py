from ServiceTrack.models import Servicio, Repuesto, Capacitacion, ObservacionIncidente, Usuario, TipoObservacion
from django import forms
from ServiceTrack.models import Servicio, Equipo, Usuario
from django.core.exceptions import ValidationError
from datetime import datetime

class ServicioForm(forms.ModelForm):
    cliente = forms.CharField(
        required=False,
        label="Cliente",
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
    )
    tecnico = forms.ModelChoiceField(
        queryset=Usuario.objects.filter(rol__nombre="tecnico"),
        required=False,
        label="Técnico",
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    fecha_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="Fecha de Finalización",
    )

    class Meta:
        model = Servicio
        fields = [
            'cliente', 'equipo', 'tecnico', 'fecha_inicio', 'fecha_fin',
            'estado', 'diagnostico_inicial', 'costo'
        ]
        widgets = {
            'equipo': forms.Select(attrs={'class': 'form-control'}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'diagnostico_inicial': forms.Textarea(attrs={'class': 'form-control'}),
            'costo': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        equipos_disponibles = kwargs.pop('equipos_disponibles', None)
        include_tecnico = kwargs.pop('include_tecnico', False)
        super().__init__(*args, **kwargs)

        # Ocultar el campo técnico si no es necesario
        if not include_tecnico:
            self.fields.pop('tecnico')

        if equipos_disponibles is not None:
            self.fields['equipo'].queryset = equipos_disponibles
            self.fields['equipo'].label_from_instance = lambda obj: (
                f"{obj.marca} {obj.modelo} - Cliente: {obj.cliente.nombre}"
            )

    def clean(self):
        """
        Validaciones adicionales
        """
        cleaned_data = super().clean()
        equipo = cleaned_data.get('equipo')
        estado = cleaned_data.get('estado')
        fecha_fin = cleaned_data.get('fecha_fin')

        # Validar que el equipo tenga un cliente asociado
        if equipo and not equipo.cliente:
            self.add_error('equipo', 'El equipo seleccionado no tiene un cliente asociado.')

        # Validar que la fecha de finalización esté presente si el estado es "completado"
        if estado == "completado" and not fecha_fin:
            self.add_error('fecha_fin', 'Debe especificar una fecha de finalización para completar el servicio.')

        return cleaned_data



class ServicioActualizarForm(ServicioForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Eliminar el campo 'cliente' del formulario
        if 'cliente' in self.fields:
            del self.fields['cliente']

class RepuestoForm(forms.ModelForm):
    class Meta:
        model = Repuesto
        fields = ['nombre', 'descripcion', 'costo', 'proveedor', 'cantidad']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control'}),
            'costo': forms.NumberInput(attrs={'class': 'form-control'}),
            'proveedor': forms.TextInput(attrs={'class': 'form-control'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class ConfirmarEntregaForm(forms.Form):
    codigo_entrega = forms.CharField(
        max_length=6,
        label="Código de Entrega",
        widget=forms.TextInput(attrs={'placeholder': 'Ingrese el código recibido', 'class': 'form-control'})
    )


class CapacitacionForm(forms.ModelForm):
    class Meta:
        model = Capacitacion
        fields = ['titulo', 'descripcion_corta', 'link']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion_corta': forms.Textarea(attrs={'class': 'form-control'}),
            'link': forms.URLInput(attrs={'class': 'form-control'}),
        }


class ClienteForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '********'}),
        label="Contraseña"
    )

    class Meta:
        model = Usuario
        fields = ['nombre', 'username', 'correo', 'cedula', 'celular', 'password']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Juan Pérez'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'jperez'}),
            'correo': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@example.com'}),
            'cedula': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '123456789'}),
            'celular': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '555-5555'}),
        }


class IncidenteForm(forms.ModelForm):
    nuevo_tipo = forms.CharField(
        required=False,
        max_length=100,
        label="Nuevo Tipo de Observación",
        help_text="Si no encuentras el tipo de observación, puedes agregar uno nuevo."
    )

    class Meta:
        model = ObservacionIncidente
        fields = ['descripcion', 'tipo_observacion', 'estado', 'fecha_reportada']
        widgets = {
            'fecha_reportada': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def save(self, commit=True):
        """
        Sobrescribe el método save para manejar la creación de un nuevo tipo de observación.
        """
        nuevo_tipo = self.cleaned_data.get('nuevo_tipo')
        if nuevo_tipo:
            tipo, created = TipoObservacion.objects.get_or_create(nombre=nuevo_tipo)
            self.instance.tipo_observacion = tipo
        return super().save(commit=commit)

class RepuestoForm(forms.ModelForm):
    class Meta:
        model = Repuesto
        fields = ['nombre', 'descripcion', 'costo', 'proveedor', 'cantidad']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control'}),
            'costo': forms.NumberInput(attrs={'class': 'form-control'}),
            'proveedor': forms.TextInput(attrs={'class': 'form-control'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class EquipoForm(forms.ModelForm):
    class Meta:
        model = Equipo
        fields = ['cliente', 'marca', 'modelo', 'anio', 'tipo_equipo', 'observaciones']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-control select2'}),
            'marca': forms.TextInput(attrs={'class': 'form-control'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control'}),
            'anio': forms.NumberInput(attrs={'class': 'form-control'}),
            'tipo_equipo': forms.TextInput(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar solo usuarios con el rol "cliente" para el campo cliente
        self.fields['cliente'].queryset = Usuario.objects.filter(rol__nombre="cliente")

    def clean_anio(self):
        """
        Valida que el año sea razonable y esté dentro del rango lógico.
        """
        anio = self.cleaned_data.get('anio')
        current_year = datetime.now().year
        min_year = 1980  # Año mínimo razonable para equipos

        if anio is not None:
            if anio < min_year:
                raise ValidationError(f"El año debe ser posterior a {min_year}.")
            if anio > current_year:
                raise ValidationError(f"El año no puede ser mayor al actual ({current_year}).")
        return anio