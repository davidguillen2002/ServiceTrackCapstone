# dashboard/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from ServiceTrack.models import Usuario, Servicio, Reto, Equipo, Rol
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.hashers import make_password
from django import forms
from django.db.models import Avg, Count, F, Sum, Value, FloatField, Case, When, DurationField, ExpressionWrapper, Q
from django.db.models.functions import TruncMonth, Coalesce
from django.core.paginator import Paginator
from datetime import datetime
from django.utils.translation import gettext as _
from calendar import monthrange, month_name
from django.utils.translation import gettext_lazy as _
from django.db.models.functions import TruncYear
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.exceptions import ValidationError
import math

@login_required
def dashboard_view(request):
    anio_filtrado = request.GET.get('anio')
    mes_filtrado = request.GET.get('mes')
    tecnico_filtrado = request.GET.get('tecnico')

    # Obtener todos los años disponibles antes de aplicar los filtros
    anios_disponibles = Servicio.objects.dates('fecha_inicio', 'year', order='DESC')

    # Filtrar servicios
    servicios = Servicio.objects.all()
    if anio_filtrado and anio_filtrado.isdigit():
        servicios = servicios.filter(fecha_inicio__year=int(anio_filtrado))
    if mes_filtrado and mes_filtrado.isdigit():
        servicios = servicios.filter(fecha_inicio__month=int(mes_filtrado))
    if tecnico_filtrado and tecnico_filtrado.isdigit():
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
            Count('tecnico_servicios', filter=Q(tecnico_servicios__estado='completado')), 0
        ),
        puntuacion_clientes=Avg('tecnico_servicios__calificacion'),
        tiempo_resolucion=ExpressionWrapper(
            Avg(F('tecnico_servicios__fecha_fin') - F('tecnico_servicios__fecha_inicio')),
            output_field=DurationField()
        )
    )

    # Rendimiento de técnicos
    tecnicos_rendimiento = Usuario.objects.filter(rol__nombre='tecnico').annotate(
        servicios_realizados=Coalesce(Count('tecnico_servicios'), 0),
        servicios_completados_count=Coalesce(
            Count('tecnico_servicios', filter=Q(tecnico_servicios__estado='completado')), 0
        ),
        rendimiento=Case(
            When(servicios_realizados=0, then=Value(0)),
            default=ExpressionWrapper(
                (F('servicios_completados_count') * 100.0) / F('servicios_realizados'),
                output_field=FloatField()
            ),
            output_field=FloatField()
        ),
        total_puntos=Coalesce(Sum('puntos'), 0),
        logros=Coalesce(Count('medallas'), 0)
    )

    # Progreso general de técnicos
    tecnicos_proceso = Usuario.objects.filter(rol__nombre='tecnico').annotate(
        progreso_servicios=Coalesce(
            Count('tecnico_servicios', filter=Q(tecnico_servicios__estado='en_progreso')), 0
        ),
        puntos_totales=Coalesce(Sum('puntos'), 0),
        ultimo_logro=F('medallas__nombre')
    )

    # Generar lista de meses con nombres en español
    meses_disponibles = [
        ("1", _("Enero")), ("2", _("Febrero")), ("3", _("Marzo")), ("4", _("Abril")),
        ("5", _("Mayo")), ("6", _("Junio")), ("7", _("Julio")), ("8", _("Agosto")),
        ("9", _("Septiembre")), ("10", _("Octubre")), ("11", _("Noviembre")), ("12", _("Diciembre"))
    ]

    context = {
        'servicios': servicios,
        'servicios_por_tecnico': list(servicios_por_tecnico),
        'estados_servicios': list(estados_servicios),
        'tecnicos_kpis': tecnicos_kpis,
        'tecnicos_rendimiento': tecnicos_rendimiento,
        'tecnicos_proceso': tecnicos_proceso,
        'anios': anios_disponibles,
        'meses': meses_disponibles,
        'anio_filtrado': anio_filtrado,
        'mes_filtrado': mes_filtrado,
        'tecnico_filtrado': tecnico_filtrado,
    }
    return render(request, 'dashboard/dashboard.html', context)


@login_required
def tecnico_dashboard_view(request):
    usuario = request.user
    anio_filtrado = request.GET.get('anio')
    mes_filtrado = request.GET.get('mes')
    page_number = request.GET.get('page', 1)

    # Filtrar servicios por técnico
    servicios = Servicio.objects.filter(tecnico=usuario)

    # Validar y aplicar filtros de año y mes
    if anio_filtrado and anio_filtrado.isdigit():
        servicios = servicios.filter(fecha_inicio__year=int(anio_filtrado))
    if mes_filtrado and mes_filtrado.isdigit():
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
    servicios_por_dia_formateado = [
        {'fecha': servicio['dia'].strftime('%Y-%m-%d'), 'total': servicio['total']}
        for servicio in servicios_por_dia if servicio['dia']
    ]

    # Tiempo promedio de resolución por servicio completado
    tiempos_resolucion = servicios.filter(estado='completado').annotate(
        tiempo_resolucion=ExpressionWrapper(
            F('fecha_fin') - F('fecha_inicio'), output_field=DurationField()
        )
    ).values('id', 'tiempo_resolucion')

    tiempos_resolucion_data = [
        {'servicio': t['id'], 'tiempo': t['tiempo_resolucion'].total_seconds() / 3600}
        for t in tiempos_resolucion if t['tiempo_resolucion']
    ]

    # Obtener años disponibles para el filtro
    anios_disponibles = servicios.dates('fecha_inicio', 'year', order='DESC')

    # Generar lista de meses con nombres en español
    meses_disponibles = [
        ("1", _("Enero")), ("2", _("Febrero")), ("3", _("Marzo")), ("4", _("Abril")),
        ("5", _("Mayo")), ("6", _("Junio")), ("7", _("Julio")), ("8", _("Agosto")),
        ("9", _("Septiembre")), ("10", _("Octubre")), ("11", _("Noviembre")), ("12", _("Diciembre"))
    ]

    # Paginación de servicios
    paginator = Paginator(servicios, 5)  # 5 servicios por página
    servicios_paginados = paginator.get_page(page_number)

    context = {
        'servicios': servicios_paginados,
        'total_servicios': total_servicios,
        'promedio_calificacion': promedio_calificacion,
        'servicios_en_progreso': servicios_en_progreso,
        'anios': anios_disponibles,
        'anio_filtrado': anio_filtrado,
        'meses': meses_disponibles,
        'mes_filtrado': mes_filtrado,
        'servicios_por_dia': servicios_por_dia_formateado,
        'tiempos_resolucion_data': tiempos_resolucion_data,
    }
    return render(request, 'dashboard/tecnico_dashboard.html', context)

@login_required
def cliente_dashboard_view(request):
    usuario = request.user
    anio_filtrado = request.GET.get('anio', None)  # Obtener filtro de año
    mes_filtrado = request.GET.get('mes', None)  # Obtener filtro de mes

    # Filtrar servicios y equipos del cliente
    equipos = Equipo.objects.filter(cliente=usuario)
    servicios = Servicio.objects.filter(equipo__cliente=usuario)

    # Aplicar filtros de año y mes
    if anio_filtrado and anio_filtrado.isdigit():
        servicios = servicios.filter(fecha_inicio__year=int(anio_filtrado))
    if mes_filtrado and mes_filtrado.isdigit():
        servicios = servicios.filter(fecha_inicio__month=int(mes_filtrado))

    # KPIs
    total_equipos = equipos.count()
    costos_totales = servicios.aggregate(Sum('costo'))['costo__sum'] or 0

    # Estados de servicios
    estados_servicios = servicios.values('estado').annotate(total=Count('id'))
    estados_totales = {"pendiente": 0, "en_progreso": 0, "completado": 0}
    for estado in estados_servicios:
        estados_totales[estado['estado']] = estado['total']

    # Años disponibles
    anios_disponibles = servicios.dates('fecha_inicio', 'year', order='DESC').distinct()

    # Lista de meses con nombres
    meses_nombres = [
        ("1", _("Enero")), ("2", _("Febrero")), ("3", _("Marzo")), ("4", _("Abril")),
        ("5", _("Mayo")), ("6", _("Junio")), ("7", _("Julio")), ("8", _("Agosto")),
        ("9", _("Septiembre")), ("10", _("Octubre")), ("11", _("Noviembre")), ("12", _("Diciembre"))
    ]

    context = {
        'equipos': equipos,
        'total_equipos': total_equipos,
        'costos_totales': costos_totales,
        'anio_filtrado': anio_filtrado,
        'mes_filtrado': mes_filtrado,
        'anios': anios_disponibles,
        'meses': meses_nombres,
        'estados_servicios': estados_totales,  # Datos para el gráfico
    }
    return render(request, 'dashboard/cliente_dashboard.html', context)

# Algoritmo para validar cédula
def verificar_cedula(cedula):
    if len(cedula) != 10:
        raise ValidationError("La cédula debe contener exactamente 10 dígitos.")
    try:
        multiplicador = [2, 1, 2, 1, 2, 1, 2, 1, 2]
        ced_array = [int(k) for k in list(cedula[:9])]
        ultimo_digito = int(cedula[9])
        resultado = []

        for i, j in zip(ced_array, multiplicador):
            prod = i * j
            resultado.append(prod if prod < 10 else prod - 9)

        suma = sum(resultado)
        verificador = (10 - (suma % 10)) if suma % 10 != 0 else 0

        if verificador != ultimo_digito:
            raise ValidationError("La cédula ingresada no es válida.")
    except ValueError:
        raise ValidationError("La cédula debe contener únicamente números.")

# Formulario personalizado con validación de cédula
class UsuarioForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '********'}),
        label="Contraseña"
    )
    cedula = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1234567890'}),
        label="Cédula",
        max_length=10
    )

    class Meta:
        model = Usuario
        fields = ['nombre', 'username', 'password', 'rol', 'cedula', 'correo', 'celular']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Juan Pérez'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'jperez'}),
            'correo': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'juan.perez@example.com'}),
            'celular': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '5551234567'}),
            'rol': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean_cedula(self):
        cedula = self.cleaned_data.get('cedula')
        verificar_cedula(cedula)  # Llama al algoritmo de validación
        return cedula

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

@login_required
def usuario_list_view(request):
    # Obtener filtros de la solicitud GET
    nombre_filtro = request.GET.get('nombre', '').strip()
    rol_filtro = request.GET.get('rol', '').strip()

    # Consultar todos los usuarios
    usuarios = Usuario.objects.all().order_by('nombre')

    # Aplicar filtros
    if nombre_filtro:
        usuarios = usuarios.filter(nombre__icontains=nombre_filtro)
    if rol_filtro.isdigit():
        usuarios = usuarios.filter(rol__id=int(rol_filtro))

    # Configurar el paginador
    page = request.GET.get('page', 1)
    paginator = Paginator(usuarios, 5)  # Mostrar 5 usuarios por página

    try:
        usuarios_paginados = paginator.page(page)
    except PageNotAnInteger:
        usuarios_paginados = paginator.page(1)
    except EmptyPage:
        usuarios_paginados = paginator.page(paginator.num_pages)

    # Pasar todos los roles al contexto para el filtro de rol
    roles = Rol.objects.all()

    context = {
        'usuarios': usuarios_paginados,
        'roles': roles,  # Para el filtro de roles en el template
    }

    return render(request, 'usuarios/usuario_list.html', context)

class UsuarioDeleteView(SuccessMessageMixin, DeleteView):
    """Vista para eliminar un usuario."""
    model = Usuario
    template_name = 'usuarios/usuario_confirm_delete.html'
    success_url = reverse_lazy('usuario-list')
    success_message = "Usuario eliminado correctamente."