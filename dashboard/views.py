# dashboard/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from ServiceTrack.models import Usuario, Servicio, Reto
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.hashers import make_password
from django import forms
from django.db.models import Avg, Count, F, Sum

@login_required
def dashboard_view(request):
    # Servicios completados por técnico
    servicios_por_tecnico = list(
        Servicio.objects.filter(estado='completado')
        .values('tecnico__nombre')
        .annotate(total=Count('id'))
    )

    # Servicios completados por mes
    servicios_por_mes = list(
        Servicio.objects.filter(estado='completado')
        .annotate(mes=F('fecha_inicio__month'))
        .values('mes')
        .annotate(total=Count('id'))
    )

    # KPIs generales
    tecnicos_kpis = Usuario.objects.filter(rol__nombre='tecnico').annotate(
        total_servicios_completados=Count(
            'tecnico_servicios', filter=F('tecnico_servicios__estado') == 'completado'
        ),
        puntuacion_clientes=Avg('tecnico_servicios__calificacion'),
        tiempo_resolucion=Avg(
            F('tecnico_servicios__fecha_fin') - F('tecnico_servicios__fecha_inicio')
        ),
    )

    # Rendimiento de técnicos
    tecnicos_rendimiento = Usuario.objects.filter(rol__nombre='tecnico').annotate(
        servicios_realizados=Count('tecnico_servicios'),
        rendimiento=(Count('tecnico_servicios', filter=F('tecnico_servicios__estado') == 'completado') * 100)
        / Count('tecnico_servicios'),
        total_puntos=Sum('puntos'),  # Renombrado para evitar conflictos
        logros=Count('medallas'),
    )

    # Progreso general de técnicos
    tecnicos_proceso = Usuario.objects.filter(rol__nombre='tecnico').annotate(
        progreso_servicios=Count('tecnico_servicios', filter=F('tecnico_servicios__estado') == 'en_progreso'),
        puntos_totales=Sum('puntos'),  # Renombrado para evitar conflictos
        ultimo_logro=F('medallas__nombre'),
    )

    # Retos dinámicos
    retos = Reto.objects.all()

    context = {
        'servicios_por_tecnico': servicios_por_tecnico,
        'servicios_por_mes': servicios_por_mes,
        'tecnicos_kpis': tecnicos_kpis,
        'tecnicos_rendimiento': tecnicos_rendimiento,
        'tecnicos_proceso': tecnicos_proceso,
        'retos': retos,
    }
    return render(request, 'dashboard/dashboard.html', context)

class UsuarioForm(forms.ModelForm):
    """Formulario personalizado para usuarios."""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '********'}),
        label="Contraseña"
    )

    class Meta:
        model = Usuario
        fields = ['nombre', 'username', 'password', 'rol', 'cedula', 'correo', 'celular']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Juan Pérez'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'jperez'}),
            'cedula': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1234567890'}),
            'correo': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'juan.perez@example.com'}),
            'celular': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '555-1234'}),
            'rol': forms.Select(attrs={'class': 'form-control'}),
        }

class UsuarioCreateForm(UsuarioForm):
    """Formulario para crear un usuario con campo de contraseña."""

class UsuarioUpdateForm(forms.ModelForm):
    """Formulario para actualizar un usuario sin el campo de contraseña."""
    class Meta:
        model = Usuario
        fields = ['nombre', 'username', 'rol', 'cedula', 'correo', 'celular']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Juan Pérez'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'jperez'}),
            'cedula': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1234567890'}),
            'correo': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'juan.perez@example.com'}),
            'celular': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '555-1234'}),
            'rol': forms.Select(attrs={'class': 'form-control'}),
        }

class UsuarioCreateView(SuccessMessageMixin, CreateView):
    """Vista para crear un nuevo usuario."""
    model = Usuario
    form_class = UsuarioCreateForm
    template_name = 'usuarios/usuario_form.html'
    success_url = reverse_lazy('usuario-list')
    success_message = "Usuario agregado correctamente."

    def form_valid(self, form):
        """Cifra la contraseña antes de guardar."""
        usuario = form.save(commit=False)
        usuario.password = make_password(form.cleaned_data['password'])
        usuario.save()
        return super().form_valid(form)

class UsuarioUpdateView(SuccessMessageMixin, UpdateView):
    """Vista para actualizar un usuario sin necesidad de cambiar la contraseña."""
    model = Usuario
    form_class = UsuarioUpdateForm
    template_name = 'usuarios/usuario_form.html'
    success_url = reverse_lazy('usuario-list')
    success_message = "Usuario actualizado correctamente."

class UsuarioListView(ListView):
    """Vista para listar todos los usuarios."""
    model = Usuario
    template_name = 'usuarios/usuario_list.html'
    context_object_name = 'usuarios'

class UsuarioDeleteView(SuccessMessageMixin, DeleteView):
    """Vista para eliminar un usuario."""
    model = Usuario
    template_name = 'usuarios/usuario_confirm_delete.html'
    success_url = reverse_lazy('usuario-list')
    success_message = "Usuario eliminado correctamente."