from django import forms
from ServiceTrack.models import Servicio, Repuesto

class ServicioForm(forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ['equipo', 'tecnico', 'fecha_inicio', 'fecha_fin', 'estado', 'calificacion', 'comentario_cliente', 'costo']

class RepuestoForm(forms.ModelForm):
    class Meta:
        model = Repuesto
        fields = ['nombre', 'descripcion', 'costo', 'proveedor', 'cantidad']