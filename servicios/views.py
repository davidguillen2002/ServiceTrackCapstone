# servicios/views.py
from django.shortcuts import render, get_object_or_404
from ServiceTrack.models import Guia, Categoria, Servicio, Usuario
from django.db.models import Q, Avg
from .ai_utils import get_similar_guides  # Asumiendo que `ai_utils.py` sigue siendo relevante

def base_conocimiento(request):
    query = request.GET.get('q', '')  # Palabras clave
    categoria_filtro = request.GET.get('categoria', '')
    tipo_servicio_filtro = request.GET.get('tipo_servicio', '')

    # Filtro por guías, categoría y tipo de servicio
    guias = Guia.objects.all()

    if query:
        guias = guias.filter(Q(titulo__icontains=query) | Q(descripcion__icontains=query))

    if categoria_filtro:
        guias = guias.filter(categoria__nombre=categoria_filtro)

    if tipo_servicio_filtro:
        guias = guias.filter(tipo_servicio__icontains=tipo_servicio_filtro)

    # Cargar las categorías y tipos de servicio para los filtros
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

def register_service(request, service_id):
    # Obtener el servicio actual por su ID
    current_service = get_object_or_404(Servicio, id=service_id)

    # Obtener las guías similares
    similar_guides = get_similar_guides(current_service)

    # Renderizar el template con las guías recomendadas
    return render(request, 'servicios/similar_guides.html', {
        'current_service': current_service,
        'similar_guides': similar_guides,
    })

def dashboard(request):
    # Obtener estadísticas
    total_servicios = Servicio.objects.count()
    calificacion_promedio = Servicio.objects.filter(calificacion__isnull=False).aggregate(Avg('calificacion'))['calificacion__avg']
    guias_mas_consultadas = Guia.objects.order_by('-puntuacion')[:5]
    tecnicos = Usuario.objects.filter(rol__nombre='tecnico')

    # Renderizar el panel de control
    return render(request, 'servicios/dashboard.html', {
        'total_servicios': total_servicios,
        'calificacion_promedio': calificacion_promedio,
        'guias_mas_consultadas': guias_mas_consultadas,
        'tecnicos': tecnicos,
    })

def guia_detalle(request, guia_id):
    guia = get_object_or_404(Guia, id=guia_id)
    return render(request, 'servicios/guia_detalle.html', {'guia': guia})