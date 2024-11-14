from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Avg
from django.contrib.auth.decorators import user_passes_test, login_required
from ServiceTrack.models import Guia, Categoria, Servicio, Usuario
from .ai_utils import get_similar_guides
from django.http import JsonResponse
from django.template.loader import render_to_string
from .forms import ServicioForm
from django.contrib import messages

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
        form = ServicioForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("lista_servicios")
    else:
        form = ServicioForm()
    return render(request, "servicios/registrar_servicio.html", {"form": form})

@login_required
@user_passes_test(is_admin)
def lista_servicios(request):
    # Recibir parámetros de búsqueda y filtros
    query = request.GET.get('q', '')
    estado_filtro = request.GET.get('estado', '')

    # Filtrar los servicios basados en los parámetros de búsqueda
    servicios = Servicio.objects.all()
    if query:
        servicios = servicios.filter(Q(equipo_modeloicontains=query) | Q(tecniconombre_icontains=query))
    if estado_filtro:
        servicios = servicios.filter(estado=estado_filtro)

    # Si es una petición AJAX, retornar solo el HTML con los resultados
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('servicios/servicio_list.html', {'servicios': servicios})
        return JsonResponse({'html': html})

    # Renderizar la página completa en caso contrario
    estados = Servicio.objects.values_list('estado', flat=True).distinct()
    return render(request, "servicios/lista_servicios.html", {
        "servicios": servicios,
        "estados": estados
    })

@login_required
@user_passes_test(is_admin)
def actualizar_servicio(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id)
    if request.method == "POST":
        form = ServicioForm(request.POST, instance=servicio)
        if form.is_valid():
            form.save()
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
        guias = guias.filter(Q(titulo_icontains=query) | Q(descripcion_icontains=query))
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
    total_servicios = Servicio.objects.count()
    # Corrige el filtro de calificación
    calificacion_promedio = Servicio.objects.filter(calificacion_isnull=False).aggregate(Avg('calificacion'))['calificacion_avg']
    guias_mas_consultadas = Guia.objects.order_by('-puntuacion')[:5]
    tecnicos = Usuario.objects.filter(rol__nombre='tecnico')

    return render(request, 'servicios/knowledge_dashboard.html', {
        'total_servicios': total_servicios,
        'calificacion_promedio': calificacion_promedio,
        'guias_mas_consultadas': guias_mas_consultadas,
        'tecnicos': tecnicos,
    })

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