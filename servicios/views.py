# servicios/views.py
from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Avg
from django.contrib.auth.decorators import user_passes_test, login_required
from ServiceTrack.models import Guia, Categoria, Servicio, Usuario
from .ai_utils import get_similar_guides
from django.http import JsonResponse
from django.template.loader import render_to_string

# Función para verificar si el usuario es técnico
def is_tecnico(user):
    return user.rol.nombre == "tecnico"

# Función para verificar si el usuario es administrador
def is_admin(user):
    return user.rol.nombre == "administrador"

@login_required
@user_passes_test(lambda u: u.rol.nombre in ["tecnico", "administrador"])
def base_conocimiento(request):
    query = request.GET.get('q', '')
    categoria_filtro = request.GET.get('categoria', '')
    tipo_servicio_filtro = request.GET.get('tipo_servicio', '')

    guias = Guia.objects.all()
    if query:
        guias = guias.filter(Q(titulo__icontains=query) | Q(descripcion__icontains=query))
    if categoria_filtro:
        guias = guias.filter(categoria__nombre=categoria_filtro)
    if tipo_servicio_filtro:
        guias = guias.filter(tipo_servicio__icontains=tipo_servicio_filtro)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('servicios/guia_list.html', {'guias': guias})
        return JsonResponse({'html': html})

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
    calificacion_promedio = Servicio.objects.filter(calificacion__isnull=False).aggregate(Avg('calificacion'))['calificacion__avg']
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