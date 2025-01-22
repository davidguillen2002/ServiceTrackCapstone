from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from ServiceTrack.models import Equipo, Servicio, Notificacion, Usuario
from .forms import ServicioEstadoForm, ResenaForm
from django.db import models
from datetime import datetime
from django.db.models import Q, Value
from django.db.models.functions import Upper, Concat

# Helper to check if the user is a technician
def is_tecnico(user):
    return user.rol.nombre == "tecnico"

# Helper to check if the user is a client
def is_cliente(user):
    return user.rol.nombre == "cliente"

# Vistas para Clientes
@login_required
@user_passes_test(is_cliente)
def lista_equipos_cliente(request):
    """
    Vista para mostrar el seguimiento de las reparaciones del cliente con paginación y filtros.
    """
    # Obtener parámetros de búsqueda
    id_servicio = request.GET.get('id', '')
    estado = request.GET.get('estado', '')
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')

    # Filtrar servicios por cliente
    servicios = Servicio.objects.filter(equipo__cliente=request.user)

    # Aplicar filtros
    if id_servicio:
        servicios = servicios.filter(id=id_servicio)
    if estado:
        servicios = servicios.filter(estado=estado)
    if fecha_inicio:
        servicios = servicios.filter(fecha_inicio__gte=fecha_inicio)
    if fecha_fin:
        servicios = servicios.filter(fecha_inicio__lte=fecha_fin)

    # Ordenar y paginar resultados
    servicios = servicios.order_by('-fecha_inicio')
    paginator = Paginator(servicios, 5)
    page_number = request.GET.get('page', 1)
    servicios_paginados = paginator.get_page(page_number)

    return render(request, 'seguimiento/lista_equipos_cliente.html', {
        'servicios': servicios_paginados,
    })

@login_required
@user_passes_test(is_cliente)
def detalle_equipo_cliente(request, equipo_id):
    """
    Vista para mostrar el detalle de un equipo específico para un cliente,
    junto con el historial de servicios y la calificación de cada servicio.
    """
    # Obtener el equipo del cliente autenticado
    equipo = get_object_or_404(Equipo, id=equipo_id, cliente=request.user)

    # Obtener los servicios asociados al equipo, ordenados por fecha de inicio descendente
    servicios = Servicio.objects.filter(equipo=equipo).order_by('-fecha_inicio')

    # Configurar la paginación (5 servicios por página)
    page = request.GET.get('page', 1)
    paginator = Paginator(servicios, 5)
    servicios_paginados = paginator.get_page(page)

    # Definir un rango para las estrellas (de 1 a 5)
    rango_estrellas = list(range(1, 6))

    # Renderizar el template con el equipo, servicios paginados y rango de estrellas
    return render(request, 'seguimiento/detalle_equipo_cliente.html', {
        'equipo': equipo,
        'servicios': servicios_paginados,
        'rango_estrellas': rango_estrellas,
    })

@login_required
@user_passes_test(is_cliente)
def dejar_resena(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id, equipo__cliente=request.user)
    rango_estrellas = range(1, 6)

    if request.method == 'POST':
        form = ResenaForm(request.POST, instance=servicio)
        if form.is_valid():
            form.save()
            # Crear notificación al administrador
            mensaje = f"El cliente {request.user.nombre} ha dejado una reseña para el servicio {servicio.id}."
            Notificacion.crear_notificacion(
                usuario=Usuario.objects.get(rol__nombre="administrador"),
                tipo="nueva_observacion",
                mensaje=mensaje
            )
            return redirect('lista_equipos_cliente')
    else:
        form = ResenaForm(instance=servicio)

    return render(request, 'seguimiento/dejar_resena.html', {
        'form': form,
        'servicio': servicio,
        'rango_estrellas': rango_estrellas,
    })

# Vistas para Técnicos
@login_required
@user_passes_test(is_tecnico)
def lista_equipos_tecnico(request):
    # Obtener solo los equipos asignados al técnico y sus servicios
    equipos = Equipo.objects.filter(servicio__tecnico=request.user).distinct()
    return render(request, 'seguimiento/lista_equipos_tecnico.html', {
        'equipos': equipos,
    })

@login_required
@user_passes_test(is_tecnico)
def actualizar_estado_equipo_tecnico(request, equipo_id):
    # Buscar el servicio activo asociado al equipo para el técnico actual
    servicio = get_object_or_404(Servicio, equipo_id=equipo_id, tecnico=request.user)

    if request.method == 'POST':
        form = ServicioEstadoForm(request.POST, instance=servicio)
        if form.is_valid():
            form.save()
            return redirect('lista_equipos_tecnico')
    else:
        form = ServicioEstadoForm(instance=servicio)

    return render(request, 'seguimiento/actualizar_estado_equipo_tecnico.html', {
        'form': form,
        'equipo': servicio.equipo,
    })

@login_required
@user_passes_test(is_tecnico)
def detalle_servicio_tecnico(request, servicio_id):
    # Verificar que el servicio pertenece al técnico
    servicio = get_object_or_404(Servicio, id=servicio_id, tecnico=request.user)
    return render(request, 'seguimiento/detalle_servicio_tecnico.html', {
        'servicio': servicio,
    })


@login_required
@user_passes_test(is_cliente)
def panel_cliente(request):
    # Obtener parámetros de búsqueda
    equipo_filtrado = request.GET.get('equipo', '').strip()  # Filtro por nombre de equipo
    estado_filtrado = request.GET.get('estado', '')  # Filtro por estado
    fecha_inicio_filtrada = request.GET.get('fecha_inicio', '')  # Filtro por fecha de recepción

    # Filtrar los servicios del cliente actual
    servicios = Servicio.objects.filter(equipo__cliente=request.user).order_by('-fecha_inicio')

    # Aplicar filtros
    if equipo_filtrado:
        # Normaliza la entrada eliminando espacios y transformando a minúsculas
        equipo_filtrado = equipo_filtrado.strip().lower()

        # Divide las palabras del filtro por espacios
        palabras = equipo_filtrado.split()

        # Construye el query dinámico para buscar cada palabra en marca o modelo
        query = Q()
        for palabra in palabras:
            query &= Q(
                Q(equipo__marca__icontains=palabra) |
                Q(equipo__modelo__icontains=palabra)
            )

        servicios = servicios.filter(query)

    if estado_filtrado:
        servicios = servicios.filter(estado=estado_filtrado)  # Filtrar por estado
    if fecha_inicio_filtrada:
        try:
            servicios = servicios.filter(fecha_inicio=datetime.strptime(fecha_inicio_filtrada, '%Y-%m-%d').date())
        except ValueError:
            pass  # Ignorar errores si la fecha no tiene el formato correcto

    # Configurar paginación
    page = request.GET.get('page', 1)
    paginator = Paginator(servicios, 5)  # Mostrar 5 servicios por página
    servicios_paginados = paginator.get_page(page)

    # Calcular estadísticas para los gráficos
    promedio_calificacion = servicios.filter(estado='completado').aggregate(models.Avg('calificacion'))['calificacion__avg'] or 0
    servicios_completados = servicios.filter(estado='completado').count()
    costo_total = servicios.aggregate(models.Sum('costo'))['costo__sum'] or 0

    return render(request, 'seguimiento/panel_cliente.html', {
        'servicios': servicios_paginados,  # Servicios paginados
        'promedio_calificacion': round(promedio_calificacion, 2),
        'servicios_completados': servicios_completados,
        'costo_total': round(costo_total, 2),
        'equipo_filtrado': equipo_filtrado,  # Valor actual del filtro por equipo
        'estado_filtrado': estado_filtrado,  # Valor actual del filtro por estado
        'fecha_inicio_filtrada': fecha_inicio_filtrada,  # Valor actual del filtro por fecha
        'estados_disponibles': ['pendiente', 'en_progreso', 'completado'],  # Estados posibles para el filtro
    })
