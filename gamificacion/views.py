# gamificacion/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from ServiceTrack.models import Usuario, Guia, ObservacionIncidente, Medalla, Reto, RegistroPuntos
from .forms import GuiaForm, ObservacionIncidenteForm, RetoForm, MedallaForm
from .utils import actualizar_puntos_usuario, asignar_medalla

# Verificación para acceder solo si el usuario es admin
def is_admin(user):
    return user.is_superuser

# Vista del perfil de gamificación para usuarios
@login_required
def perfil_gamificacion(request):
    usuario = request.user
    puntos = actualizar_puntos_usuario(usuario)
    asignar_medalla(usuario)
    medallas = usuario.medallas.all()
    return render(request, 'gamificacion/perfil_gamificacion.html', {'usuario': usuario, 'puntos': puntos, 'medallas': medallas})

# Vista para ver retos disponibles
@login_required
def retos_disponibles(request):
    retos = Reto.objects.all()
    return render(request, 'gamificacion/retos_disponibles.html', {'retos': retos})

# Historial de puntos para el usuario actual
@login_required
def historial_puntos(request):
    registros = RegistroPuntos.objects.filter(usuario=request.user).order_by('-fecha')
    return render(request, 'gamificacion/historial_puntos.html', {'registros': registros})

# Panel de Administración solo para admin
@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    tecnicos = Usuario.objects.filter(rol__nombre="tecnico")
    total_tecnicos = tecnicos.count()
    total_puntos = RegistroPuntos.objects.aggregate(total=Sum('puntos_obtenidos'))['total'] or 0
    total_retos = Reto.objects.count()
    total_medallas = Medalla.objects.count()

    progreso_tecnicos = []
    for tecnico in tecnicos:
        retos_completados = RegistroPuntos.objects.filter(usuario=tecnico, descripcion__icontains="reto").count()
        medallas_desbloqueadas = tecnico.medallas.count()
        puntos_acumulados = tecnico.puntos
        progreso_tecnicos.append({
            'nombre': tecnico.nombre,
            'puntos_acumulados': puntos_acumulados,
            'retos_completados': retos_completados,
            'medallas_desbloqueadas': medallas_desbloqueadas,
        })

    context = {
        'total_tecnicos': total_tecnicos,
        'total_puntos': total_puntos,
        'total_retos': total_retos,
        'total_medallas': total_medallas,
        'progreso_tecnicos': progreso_tecnicos,
    }

    return render(request, 'gamificacion/admin_dashboard.html', context)

# CRUD para Guías
@login_required
def lista_guias(request):
    guias = Guia.objects.all()
    return render(request, 'gamificacion/lista_guias.html', {'guias': guias})

@login_required
def crear_guia(request):
    if request.method == 'POST':
        form = GuiaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_guias')
    else:
        form = GuiaForm()
    return render(request, 'gamificacion/crear_guia.html', {'form': form})

@login_required
def editar_guia(request, guia_id):
    guia = get_object_or_404(Guia, id=guia_id)
    if request.method == 'POST':
        form = GuiaForm(request.POST, instance=guia)
        if form.is_valid():
            form.save()
            return redirect('lista_guias')
    else:
        form = GuiaForm(instance=guia)
    return render(request, 'gamificacion/editar_guia.html', {'form': form})

@login_required
def eliminar_guia(request, guia_id):
    guia = get_object_or_404(Guia, id=guia_id)
    guia.delete()
    return redirect('lista_guias')

# CRUD para Observaciones de Incidentes
@login_required
def lista_observaciones(request):
    observaciones = ObservacionIncidente.objects.all()
    return render(request, 'gamificacion/lista_observaciones.html', {'observaciones': observaciones})

@login_required
def crear_observacion(request):
    if request.method == 'POST':
        form = ObservacionIncidenteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_observaciones')
    else:
        form = ObservacionIncidenteForm()
    return render(request, 'gamificacion/crear_observacion.html', {'form': form})

@login_required
def editar_observacion(request, observacion_id):
    observacion = get_object_or_404(ObservacionIncidente, id=observacion_id)
    if request.method == 'POST':
        form = ObservacionIncidenteForm(request.POST, instance=observacion)
        if form.is_valid():
            form.save()
            return redirect('lista_observaciones')
    else:
        form = ObservacionIncidenteForm(instance=observacion)
    return render(request, 'gamificacion/editar_observacion.html', {'form': form})

@login_required
def eliminar_observacion(request, observacion_id):
    observacion = get_object_or_404(ObservacionIncidente, id=observacion_id)
    observacion.delete()
    return redirect('lista_observaciones')

# CRUD para Retos (solo admin)
@login_required
@user_passes_test(is_admin)
def lista_retos(request):
    retos = Reto.objects.all()
    return render(request, 'gamificacion/lista_retos.html', {'retos': retos})

@login_required
@user_passes_test(is_admin)
def crear_reto(request):
    if request.method == 'POST':
        form = RetoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_retos')
    else:
        form = RetoForm()
    return render(request, 'gamificacion/crear_reto.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def editar_reto(request, reto_id):
    reto = get_object_or_404(Reto, id=reto_id)
    if request.method == 'POST':
        form = RetoForm(request.POST, instance=reto)
        if form.is_valid():
            form.save()
            return redirect('lista_retos')
    else:
        form = RetoForm(instance=reto)
    return render(request, 'gamificacion/editar_reto.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def eliminar_reto(request, reto_id):
    reto = get_object_or_404(Reto, id=reto_id)
    reto.delete()
    return redirect('lista_retos')

# CRUD para Medallas (solo admin)
@login_required
@user_passes_test(is_admin)
def lista_medallas(request):
    medallas = Medalla.objects.all()
    return render(request, 'gamificacion/lista_medallas.html', {'medallas': medallas})

@login_required
@user_passes_test(is_admin)
def crear_medalla(request):
    if request.method == 'POST':
        form = MedallaForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('lista_medallas')
    else:
        form = MedallaForm()
    return render(request, 'gamificacion/crear_medalla.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def editar_medalla(request, medalla_id):
    medalla = get_object_or_404(Medalla, id=medalla_id)
    if request.method == 'POST':
        form = MedallaForm(request.POST, request.FILES, instance=medalla)
        if form.is_valid():
            form.save()
            return redirect('lista_medallas')
    else:
        form = MedallaForm(instance=medalla)
    return render(request, 'gamificacion/editar_medalla.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def eliminar_medalla(request, medalla_id):
    medalla = get_object_or_404(Medalla, id=medalla_id)
    medalla.delete()
    return redirect('lista_medallas')