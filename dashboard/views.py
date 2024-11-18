# dashboard/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from ServiceTrack.models import Usuario, Servicio, Reto, Equipo
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.hashers import make_password
from django import forms
from django.db.models import Avg, Count, F, Sum, Value, FloatField, Case, When, DurationField, ExpressionWrapper, Q
from django.db.models.functions import TruncMonth, Coalesce
from datetime import datetime
from calendar import monthrange

@login_required
def dashboard_view(request):
    # Filtros para los servicios (por mes o técnico)
    mes_filtrado = request.GET.get('mes', None)
    tecnico_filtrado = request.GET.get('tecnico', None)

    servicios = Servicio.objects.all()
    if mes_filtrado:
        servicios = servicios.filter(fecha_inicio__month=int(mes_filtrado))
    if tecnico_filtrado:
        servicios = servicios.filter(tecnico__id=int(tecnico_filtrado))

    # Servicios completados por técnico
    servicios_por_tecnico = (
        servicios.filter(estado='completado')
        .values('tecnico__nombre')
        .annotate(total=Coalesce(Count('id'), Value(0)))
    )

    # Proporción de estados de servicios
    estados_servicios = (
        servicios.values('estado')
        .annotate(total=Count('id'))
    )

    # KPIs generales
    tecnicos_kpis = Usuario.objects.filter(rol__nombre='tecnico').annotate(
        total_servicios_completados=Coalesce(
            Count('tecnico_servicios', filter=Q(tecnico_servicios__estado='completado')), 0),
        puntuacion_clientes=Avg('tecnico_servicios__calificacion'),
        tiempo_resolucion=ExpressionWrapper(
            Avg(F('tecnico_servicios__fecha_fin') - F('tecnico_servicios__fecha_inicio')),
            output_field=DurationField()
        )
    )

    # Rendimiento de técnicos
    tecnicos_rendimiento = Usuario.objects.filter(rol__nombre='tecnico').annotate(
        servicios_realizados=Coalesce(Count('tecnico_servicios'), 0),
        servicios_completados_anotados=Coalesce(
            Count('tecnico_servicios', filter=Q(tecnico_servicios__estado='completado')), 0),
        rendimiento=Case(
            When(servicios_realizados=0, then=Value(0.0)),
            default=ExpressionWrapper(
                (F('servicios_completados_anotados') * 100.0) / F('servicios_realizados'),
                output_field=FloatField()
            ),
            output_field=FloatField(),  # Especificamos el tipo de salida como FloatField
        ),
        total_puntos=Coalesce(Sum('puntos'), 0),
        logros=Coalesce(Count('medallas'), 0),
    )

    # Progreso general de técnicos
    tecnicos_proceso = Usuario.objects.filter(rol__nombre='tecnico').annotate(
        progreso_servicios=Coalesce(Count('tecnico_servicios', filter=Q(tecnico_servicios__estado='en_progreso')), 0),
        puntos_totales=Coalesce(Sum('puntos'), 0),
        ultimo_logro=F('medallas__nombre'),
    )

    # Retos dinámicos
    retos = Reto.objects.all()

    # Contexto
    context = {
        'servicios': servicios,
        'servicios_por_tecnico': list(servicios_por_tecnico),  # Lista para graficar
        'estados_servicios': list(estados_servicios),          # Lista para graficar
        'tecnicos_kpis': tecnicos_kpis,
        'tecnicos_rendimiento': tecnicos_rendimiento,
        'tecnicos_proceso': tecnicos_proceso,
        'retos': retos,
        'mes_filtrado': mes_filtrado,
        'tecnico_filtrado': tecnico_filtrado,
        'meses': range(1, 13),
    }
    return render(request, 'dashboard/dashboard.html', context)

@login_required
def tecnico_dashboard_view(request):
    usuario = request.user
    mes_filtrado = request.GET.get('mes', None)

    # Filtrar servicios por técnico y mes
    servicios = Servicio.objects.filter(tecnico=usuario)
    if mes_filtrado:
        servicios = servicios.filter(fecha_inicio__month=int(mes_filtrado))

    # KPIs
    total_servicios = servicios.filter(estado='completado').count()
    promedio_calificacion = servicios.aggregate(Avg('calificacion'))['calificacion__avg'] or 0
    servicios_en_progreso = servicios.filter(estado='en_progreso').count()

    # Progreso diario
    servicios_por_dia = (
        servicios.filter(estado='completado')
        .annotate(dia=F('fecha_inicio'))
        .values('dia')
        .annotate(total=Count('id'))
        .order_by('dia')
    )

    # Formatear las fechas para el gráfico
    servicios_por_dia_formateado = [
        {'fecha': servicio['dia'].strftime('%Y-%m-%d'), 'total': servicio['total']}
        for servicio in servicios_por_dia if servicio['dia']  # Verificar que haya fecha
    ]

    # Tiempo promedio de resolución por servicio completado
    tiempos_resolucion = servicios.filter(estado='completado').annotate(
        tiempo_resolucion=ExpressionWrapper(
            F('fecha_fin') - F('fecha_inicio'), output_field=DurationField()
        )
    ).values('id', 'tiempo_resolucion')

    tiempos_resolucion_data = [
        {'servicio': t['id'], 'tiempo': t['tiempo_resolucion'].total_seconds() / 3600}
        for t in tiempos_resolucion if t['tiempo_resolucion']  # Verificar que haya tiempo
    ]

    context = {
        'servicios': servicios,
        'total_servicios': total_servicios,
        'promedio_calificacion': promedio_calificacion,
        'servicios_en_progreso': servicios_en_progreso,
        'meses': range(1, 13),
        'mes_filtrado': mes_filtrado,
        'servicios_por_dia': servicios_por_dia_formateado,  # Datos para el gráfico
        'tiempos_resolucion_data': tiempos_resolucion_data,  # Datos para el gráfico
    }
    return render(request, 'dashboard/tecnico_dashboard.html', context)

@login_required
def cliente_dashboard_view(request):
    usuario = request.user
    mes_filtrado = request.GET.get('mes', None)

    # Equipos y servicios asociados al cliente
    equipos = Equipo.objects.filter(cliente=usuario)
    servicios = Servicio.objects.filter(equipo__cliente=usuario)
    if mes_filtrado:
        servicios = servicios.filter(fecha_inicio__month=int(mes_filtrado))

    # KPIs
    total_equipos = equipos.count()
    costos_totales = servicios.aggregate(Sum('costo'))['costo__sum'] or 0

    # Estados de servicios
    estados_servicios = (
        servicios.values('estado')
        .annotate(total=Count('id'))
        .order_by('estado')
    )

    # Datos para el gráfico de barras apiladas
    estados_totales = {"pendiente": 0, "en_progreso": 0, "completado": 0}
    for estado in estados_servicios:
        estados_totales[estado['estado']] = estado['total']

    context = {
        'equipos': equipos,
        'total_equipos': total_equipos,
        'costos_totales': costos_totales,
        'mes_filtrado': mes_filtrado,
        'meses': range(1, 13),
        'estados_servicios': estados_totales,  # Datos para el gráfico
    }
    return render(request, 'dashboard/cliente_dashboard.html', context)

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