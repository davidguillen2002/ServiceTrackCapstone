from django import forms
from ServiceTrack.models import Servicio, Repuesto, Capacitacion

class ServicioForm(forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ['equipo', 'tecnico', 'fecha_inicio', 'fecha_fin', 'estado', 'calificacion', 'comentario_cliente', 'costo']

class RepuestoForm(forms.ModelForm):
    class Meta:
        model = Repuesto
        fields = ['nombre', 'descripcion', 'costo', 'proveedor', 'cantidad']

class ConfirmarEntregaForm(forms.Form):
    codigo_entrega = forms.CharField(
        max_length=6,
        label="Código de Entrega",
        widget=forms.TextInput(attrs={'placeholder': 'Ingrese el código recibido'})
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