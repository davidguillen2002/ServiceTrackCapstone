from django import forms
from ServiceTrack.models import Servicio, Repuesto, Capacitacion, ObservacionIncidente, Usuario, TipoObservacion

from django import forms
from ServiceTrack.models import Servicio, Equipo, Usuario

class ServicioForm(forms.ModelForm):
    cliente = forms.CharField(
        required=False,
        label="Cliente",
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
    )

    class Meta:
        model = Servicio
        fields = ['cliente', 'equipo', 'tecnico', 'fecha_inicio', 'estado', 'diagnostico_inicial', 'costo']
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'diagnostico_inicial': forms.Textarea(attrs={'class': 'form-control'}),
            'costo': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        equipos_disponibles = kwargs.pop('equipos_disponibles', None)
        super().__init__(*args, **kwargs)

        if equipos_disponibles is not None:
            self.fields['equipo'].queryset = equipos_disponibles

    def clean(self):
        """
        Valida que el equipo seleccionado tenga un cliente asociado.
        """
        cleaned_data = super().clean()
        equipo = cleaned_data.get('equipo')

        if equipo and not equipo.cliente:
            self.add_error('equipo', 'El equipo seleccionado no tiene un cliente asociado.')
        else:
            cleaned_data['cliente'] = equipo.cliente.nombre

        return cleaned_data


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
            'observaciones': forms.Textarea(attrs={'rows': 3}),
        }