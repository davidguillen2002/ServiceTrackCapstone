from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Avg, F, Q, FloatField, ExpressionWrapper, Count
from django.db.models.functions import Coalesce
from django.contrib.auth.decorators import user_passes_test, login_required
from ServiceTrack.models import Guia, Categoria, Servicio, Usuario, Notificacion, Equipo
from .ai_utils import get_similar_guides
from django.http import JsonResponse
from django.template.loader import render_to_string
from .forms import ServicioForm, RepuestoForm
from django.contrib import messages
from django.core.paginator import Paginator

# Función para verificar si el usuario es técnico
def is_tecnico(user):
    return user.rol.nombre == "tecnico"

# Función para verificar si el usuario es administrador
def is_admin(user):
    return user.rol.nombre == "administrador"

@login_required
@user_passes_test(is_admin)
def registrar_servicio(request):
    if request.method == "POST":
        servicio_form = ServicioForm(request.POST)
        repuesto_form = RepuestoForm(request.POST)
        if servicio_form.is_valid() and repuesto_form.is_valid():
            servicio = servicio_form.save(commit=False)

            # Asignar el mejor técnico
            tecnicos = Usuario.objects.filter(rol__nombre='tecnico').annotate(
                rendimiento=ExpressionWrapper(
                    Coalesce(F('calificacion_promedio'), 0.0) * Coalesce(F('servicios_completados'), 1),
                    output_field=FloatField()
                )
            )
            mejor_tecnico = tecnicos.order_by('-rendimiento').first()
            servicio.tecnico = mejor_tecnico
            servicio.save()

            # Guardar repuesto asociado
            repuesto = repuesto_form.save(commit=False)
            repuesto.servicio = servicio
            repuesto.save()

            # Crear notificación al técnico
            Notificacion.crear_notificacion(
                usuario=mejor_tecnico,
                tipo='nuevo_servicio',
                mensaje=f"Nuevo servicio asignado al equipo {servicio.equipo.marca} {servicio.equipo.modelo}."
            )

            return redirect("lista_servicios")
    else:
        servicio_form = ServicioForm()
        repuesto_form = RepuestoForm()

    return render(request, "servicios/registrar_servicio.html", {
        "servicio_form": servicio_form,
        "repuesto_form": repuesto_form
    })

@login_required
@user_passes_test(is_admin)
def lista_servicios(request):
    # Recibir parámetros de búsqueda y filtros
    query = request.GET.get('q', '')
    estado_filtro = request.GET.get('estado', '')

    # Filtrar los servicios basados en los parámetros de búsqueda
    servicios = Servicio.objects.all()
    if query:
        servicios = servicios.filter(Q(equipo__modelo__icontains=query) | Q(tecnico__nombre__icontains=query))
    if estado_filtro:
        servicios = servicios.filter(estado=estado_filtro)

    # Obtener los estados únicos para el filtro
    estados = Servicio.objects.values_list('estado', flat=True).distinct().order_by('estado')

    # Paginación: Mostrar 5 servicios por página
    paginator = Paginator(servicios, 5)
    page_number = request.GET.get('page', 1)
    servicios_paginados = paginator.get_page(page_number)

    # Si es una solicitud AJAX, devolver solo el contenido filtrado
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('servicios/servicio_list.html', {'servicios': servicios_paginados})
        return JsonResponse({'html': html})

    # En caso de una solicitud normal, renderizar la página completa
    return render(request, "servicios/lista_servicios.html", {
        "servicios": servicios_paginados,
        "estados": estados,
    })

@login_required
@user_passes_test(is_admin)
def actualizar_servicio(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id)
    if request.method == "POST":
        form = ServicioForm(request.POST, instance=servicio)
        if form.is_valid():
            form.save()

            # Notificación para el cliente si el servicio se completa
            if servicio.estado == "completado":
                Notificacion.crear_notificacion(
                    usuario=servicio.equipo.cliente,
                    tipo="servicio_completado",
                    mensaje=f"Su servicio para el equipo {servicio.equipo.marca} {servicio.equipo.modelo} ha sido completado."
                )

            # No se necesita enviar WebSocket directamente aquí
            return redirect("lista_servicios")
    else:
        form = ServicioForm(instance=servicio)
    return render(request, "servicios/actualizar_servicio.html", {"form": form, "servicio": servicio})

@login_required
@user_passes_test(is_admin)
def eliminar_servicio(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id)
    if request.method == "POST":
        servicio.delete()
        messages.success(request, "Servicio eliminado correctamente.")
        return redirect("lista_servicios")  # Redirige a la lista de servicios después de eliminar
    return render(request, "servicios/eliminar_servicio.html", {"servicio": servicio})

def historial_servicios(request, equipo_id):
    equipo = get_object_or_404(Equipo, id=equipo_id)
    servicios = Servicio.objects.filter(equipo=equipo).order_by('-fecha_inicio')

    return render(request, 'servicios/historial_servicios.html', {
        'equipo': equipo,
        'servicios': servicios
    })

@login_required
@user_passes_test(is_tecnico)
def tecnico_services_list(request):
    """Vista para mostrar todos los servicios asociados a un técnico."""
    services = Servicio.objects.filter(tecnico=request.user)
    return render(request, 'servicios/tecnico_services_list.html', {'services': services})

@login_required
@user_passes_test(is_tecnico)
def register_service(request, service_id):
    """Vista para obtener guías recomendadas para un servicio específico del técnico."""
    current_service = get_object_or_404(Servicio, id=service_id, tecnico=request.user)
    similar_guides = get_similar_guides(current_service)
    return render(request, 'servicios/similar_guides.html', {
        'current_service': current_service,
        'similar_guides': similar_guides,
    })

@login_required
@user_passes_test(lambda u: u.rol.nombre in ["tecnico", "administrador"])
def base_conocimiento(request):
    query = request.GET.get('q', '')
    categoria_filtro = request.GET.get('categoria', '')
    tipo_servicio_filtro = request.GET.get('tipo_servicio', '')

    # Filtrar guías con los criterios de búsqueda
    guias = Guia.objects.all()
    if query:
        guias = guias.filter(Q(titulo__icontains=query) | Q(descripcion__icontains=query))
    if categoria_filtro:
        guias = guias.filter(categoria__nombre=categoria_filtro)
    if tipo_servicio_filtro:
        guias = guias.filter(tipo_servicio__icontains=tipo_servicio_filtro)

    # Si es una solicitud AJAX, devolver solo el HTML con los resultados
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('servicios/guia_list.html', {'guias': guias})
        return JsonResponse({'html': html})

    # En caso contrario, renderizar la página completa
    categorias = Categoria.objects.all()
    tipos_servicio = Guia.objects.values_list('tipo_servicio', flat=True).distinct()

    return render(request, 'servicios/base_conocimiento.html', {
        'guias': guias,
        'categorias': categorias,
        'tipos_servicio': tipos_servicio,
        'query': query,
        'categoria_filtro': categoria_filtro,
        'tipo_servicio_filtro': tipo_servicio_filtro
    })

@login_required
@user_passes_test(is_admin)
def knowledge_dashboard(request):
    servicios_por_estado = (
        Servicio.objects.values('estado')  # Agrupar por estado
        .annotate(total=Count('id'))       # Contar servicios por estado
        .order_by('estado')                # Ordenar por estado
    )
    labels = [item['estado'] for item in servicios_por_estado]  # Etiquetas para el gráfico
    data = [item['total'] for item in servicios_por_estado]     # Datos para el gráfico

    total_servicios = Servicio.objects.count()
    calificacion_promedio = Servicio.objects.filter(calificacion__isnull=False).aggregate(Avg('calificacion'))['calificacion__avg']
    guias_mas_consultadas = Guia.objects.order_by('-puntuacion')[:5]
    tecnicos = Usuario.objects.filter(rol__nombre='tecnico')

    context = {
        'labels': labels,
        'data': data,
        'total_servicios': total_servicios,
        'calificacion_promedio': calificacion_promedio,
        'guias_mas_consultadas': guias_mas_consultadas,
        'tecnicos': tecnicos,
    }
    return render(request, 'servicios/knowledge_dashboard.html', context)

@login_required
@user_passes_test(lambda u: u.rol.nombre in ["tecnico", "administrador"])
def guia_detalle(request, guia_id):
    guia = get_object_or_404(Guia, id=guia_id)
    return render(request, 'servicios/guia_detalle.html', {'guia': guia})

@login_required
@user_passes_test(lambda u: u.rol.nombre in ["tecnico", "administrador"])
def register_service(request, service_id):
    current_service = get_object_or_404(Servicio, id=service_id)
    similar_guides = get_similar_guides(current_service)
    return render(request, 'servicios/similar_guides.html', {
        'current_service': current_service,
        'similar_guides': similar_guides,
    })

@login_required
def detalle_servicio(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id)
    repuestos = servicio.repuestos.all()  # Acceder a los repuestos relacionados
    return render(request, 'servicios/detalle_servicio.html', {
        'servicio': servicio,
        'repuestos': repuestos
    })