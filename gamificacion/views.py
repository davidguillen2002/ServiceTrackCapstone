from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Avg, F, Count
from django import forms
from django.contrib import messages
from django.utils.timezone import now
from django.views.decorators.cache import never_cache

from ServiceTrack.models import Usuario, Medalla, Reto, RegistroPuntos, RetoUsuario, Guia, ObservacionIncidente, \
    Servicio, Recompensa, RetoCliente
from .forms import GuiaForm, ObservacionIncidenteForm, RetoForm, MedallaForm
from .utils import (
    otorgar_puntos_por_servicio,
    verificar_y_asignar_medallas_y_retos,
    generar_recomendaciones_para_tecnico,
    asignar_retos_dinamicos,
    otorgar_experiencia,
    generar_recomendaciones_con_ia,
)
from .notifications import notificar_tecnico, notificar_tecnico_con_animacion


class OtorgarPuntosForm(forms.Form):
    usuario = forms.ModelChoiceField(queryset=Usuario.objects.filter(rol__nombre="tecnico"))
    puntos = forms.IntegerField(min_value=1)
    descripcion = forms.CharField(max_length=255)

@login_required
def otorgar_puntos_view(request):
    """
    Vista para otorgar puntos a un técnico con retroalimentación visual.
    """

    usuario = request.user

    # Validar si el usuario tiene rol de administrador
    if usuario.rol.nombre != "administrador":
        messages.error(request, "Acceso denegado.")
        return redirect("home")

    if request.method == 'POST':
        form = OtorgarPuntosForm(request.POST)
        if form.is_valid():
            usuario = form.cleaned_data['usuario']
            puntos = form.cleaned_data['puntos']
            descripcion = form.cleaned_data['descripcion']

            usuario.puntos += puntos
            usuario.save()

            RegistroPuntos.objects.create(usuario=usuario, puntos_obtenidos=puntos, descripcion=descripcion)

            verificar_y_asignar_medallas_y_retos(usuario)
            notificar_tecnico_con_animacion(usuario, f"¡Has recibido {puntos} puntos! {descripcion}", animacion="rubberBand")

            messages.success(request, f"{puntos} puntos otorgados a {usuario.nombre} con éxito.")
            return redirect('admin_dashboard_gamificacion')
    else:
        form = OtorgarPuntosForm()

    return render(request, 'gamificacion/otorgar_puntos.html', {'form': form})

@login_required
def perfil_gamificacion(request):
    usuario = request.user

    if usuario.rol.nombre != "tecnico":
        messages.error(request, "Acceso denegado.")
        return redirect("home")

    # Calcular experiencia basada en retos cumplidos (solo si no se ha calculado previamente)
    retos_cumplidos = RetoUsuario.objects.filter(usuario=usuario, cumplido=True)
    experiencia_real = retos_cumplidos.aggregate(total_experiencia=Sum('reto__puntos_otorgados'))['total_experiencia'] or 0
    if usuario.experiencia < experiencia_real:
        usuario.experiencia = experiencia_real
        usuario.save()

    # Verificar si el usuario puede subir de nivel
    usuario.verificar_y_subir_nivel()

    # Calcular experiencia requerida y progreso del nivel
    experiencia_requerida = usuario.calcular_experiencia_nivel_siguiente()
    progreso_nivel = (
        round((usuario.experiencia / experiencia_requerida) * 100, 2)
        if experiencia_requerida > 0 else 0
    )

    # Verificar y asignar medallas y retos
    animaciones = verificar_y_asignar_medallas_y_retos(usuario)

    # Filtrar medallas asociadas a retos del nivel actual
    medallas_nivel = Medalla.objects.filter(retos_asociados__nivel=usuario.nivel).distinct()
    medallas_usuario = usuario.medallas.all()

    # Obtener retos disponibles del nivel actual
    retos_disponibles = RetoUsuario.objects.filter(
        usuario=usuario, cumplido=False, reto__nivel=usuario.nivel
    ).select_related('reto')[:3]

    # Generar enlaces para redirigir a la lista de servicios según el reto
    for reto_usuario in retos_disponibles:
        reto_usuario.servicios_url = f"/servicios/tecnico_services/"

    # Calcular progreso de medallas
    total_medallas = medallas_nivel.count()
    progreso_medallas = (
        round((medallas_usuario.filter(id__in=medallas_nivel).count() / total_medallas) * 100, 2)
        if total_medallas > 0 else 0
    )

    # Calcular promedio de calificaciones
    calificacion_promedio = (
        Servicio.objects.filter(tecnico=usuario, estado="completado")
        .aggregate(promedio=Avg("calificacion"))["promedio"]
        or 0
    )

    # Generar recomendaciones personalizadas
    recomendaciones = generar_recomendaciones_con_ia(usuario)
    recomendaciones_procesadas = [recomendacion for recomendacion in recomendaciones]

    return render(request, "gamificacion/perfil_gamificacion.html", {
        "usuario": usuario,
        "medallas_nivel": medallas_nivel,
        "medallas_usuario": medallas_usuario,
        "progreso_medallas": progreso_medallas,
        "calificacion_promedio": round(calificacion_promedio, 2),
        "progreso_nivel": progreso_nivel,
        "experiencia_actual": usuario.experiencia,
        "experiencia_requerida": experiencia_requerida,
        "retos_disponibles": retos_disponibles,
        "recomendaciones": recomendaciones_procesadas,
        "animaciones": animaciones,
    })

@login_required
def admin_dashboard(request):
    """
    Vista del panel de administración con métricas clave.
    """
    usuario = request.user

    # Validar si el usuario tiene rol de administrador
    if usuario.rol.nombre != "administrador":
        messages.error(request, "Acceso denegado.")
        return redirect("home")

    # Consultar datos de los técnicos
    tecnicos = Usuario.objects.filter(rol__nombre="tecnico").annotate(
        puntos_acumulados=Sum('registropuntos__puntos_obtenidos'),
        total_retos_completados=Count('retos_usuario', filter=F('retos_usuario__cumplido')),
        medallas_desbloqueadas=Count('medallas'),
        promedio_calificaciones=Avg('tecnico_servicios__calificacion', filter=F('tecnico_servicios__estado') == 'completado'),
    )

    # Calcular métricas clave
    total_tecnicos = tecnicos.count()
    total_puntos = RegistroPuntos.objects.aggregate(total=Sum('puntos_obtenidos'))['total'] or 0
    total_retos = Reto.objects.count()
    total_medallas = Medalla.objects.count()

    return render(request, 'gamificacion/admin_dashboard.html', {
        'total_tecnicos': total_tecnicos,
        'total_puntos': total_puntos,
        'total_retos': total_retos,
        'total_medallas': total_medallas,
        'progreso_tecnicos': tecnicos,
    })

@login_required
def explorar_retos(request):
    usuario = request.user

    if not hasattr(usuario, 'rol') or usuario.rol.nombre != "tecnico":
        messages.error(request, "Acceso denegado.")
        return redirect("home")

    # Asignar retos dinámicos si aún no los tiene
    asignar_retos_dinamicos(usuario)

    # Consultar retos pendientes y completados
    retos_pendientes = RetoUsuario.objects.filter(
        usuario=usuario,
        cumplido=False,
        reto__nivel=usuario.nivel
    ).select_related('reto')

    retos_completados = RetoUsuario.objects.filter(
        usuario=usuario,
        cumplido=True,
        reto__nivel=usuario.nivel
    ).select_related('reto')

    # Generar enlaces para redirigir a los servicios relacionados con cada reto
    for reto_usuario in retos_pendientes:
        reto_usuario.servicios_url = f"/servicios/tecnico_services/"

    # Calcular el progreso general de los retos
    total_retos = retos_pendientes.count() + retos_completados.count()
    progreso_retos = round((retos_completados.count() / total_retos) * 100, 2) if total_retos > 0 else 0

    return render(request, 'gamificacion/explorar_retos.html', {
        'usuario': usuario,
        'retos_pendientes': retos_pendientes,
        'retos_completados': retos_completados,
        'progreso_retos': progreso_retos,
    })

@login_required
def nuevo_ranking_global(request):
    """
    Nueva vista para el ranking global de técnicos.
    """

    tecnicos = list(
        Usuario.objects.filter(rol__nombre="tecnico").annotate(
            puntos_totales=F('puntos')
        ).order_by('-nivel', '-puntos_totales')
    )

    return render(request, 'gamificacion/nuevo_ranking_global.html', {'tecnicos': tecnicos})


@login_required
def historial_puntos_paginated(request):
    """
    Vista para mostrar el historial de puntos con paginación.
    """
    usuario = request.user

    # Obtener registros del usuario actual ordenados por fecha
    registros = RegistroPuntos.objects.filter(usuario=usuario).order_by('-fecha')

    # Paginación
    paginator = Paginator(registros, 10)  # 10 registros por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'gamificacion/historial_puntos_paginated.html', {'page_obj': page_obj})


@login_required
def recompensas_disponibles(request):
    """
    Muestra las recompensas disponibles y posibles según el nivel actual del técnico.
    """
    usuario = request.user
    nivel_actual = usuario.nivel

    # Recompensas específicas por nivel
    recompensas_por_nivel = {
        1: [
            {"tipo": "herramienta", "valor": 50.00, "puntos_necesarios": 100, "descripcion": "Juego de destornilladores básico."},
            {"tipo": "capacitacion", "valor": 0.00, "puntos_necesarios": 120, "descripcion": "Acceso a un curso básico de reparaciones."},
            {"tipo": "reconocimiento", "valor": 0.00, "puntos_necesarios": 80, "descripcion": "Certificado de técnico en entrenamiento."},
        ],
        2: [
            {"tipo": "herramienta", "valor": 100.00, "puntos_necesarios": 200, "descripcion": "Multímetro digital profesional."},
            {"tipo": "capacitacion", "valor": 0.00, "puntos_necesarios": 220, "descripcion": "Curso avanzado de diagnóstico y reparación."},
            {"tipo": "reconocimiento", "valor": 0.00, "puntos_necesarios": 180, "descripcion": "Placa de reconocimiento al mérito técnico."},
        ],
        3: [
            {"tipo": "herramienta", "valor": 200.00, "puntos_necesarios": 300, "descripcion": "Set completo de herramientas de precisión."},
            {"tipo": "bono", "valor": 150.00, "puntos_necesarios": 320, "descripcion": "Bono por desempeño destacado en reparaciones."},
            {"tipo": "capacitacion", "valor": 0.00, "puntos_necesarios": 280, "descripcion": "Curso especializado en tecnología avanzada."},
        ],
        4: [
            {"tipo": "herramienta", "valor": 300.00, "puntos_necesarios": 500, "descripcion": "Equipo avanzado de diagnóstico electrónico."},
            {"tipo": "bono", "valor": 200.00, "puntos_necesarios": 520, "descripcion": "Bono por liderar proyectos técnicos."},
            {"tipo": "reconocimiento", "valor": 0.00, "puntos_necesarios": 480, "descripcion": "Trofeo técnico destacado del año."},
        ],
        5: [
            {"tipo": "herramienta", "valor": 500.00, "puntos_necesarios": 1000, "descripcion": "Estación de soldadura de alta precisión."},
            {"tipo": "bono", "valor": 300.00, "puntos_necesarios": 1020, "descripcion": "Bono especial por maestría técnica."},
            {"tipo": "reconocimiento", "valor": 0.00, "puntos_necesarios": 980, "descripcion": "Inscripción en el salón de la fama técnica."},
        ],
    }

    # Obtener recompensas disponibles desde la base de datos
    recompensas_disponibles = Recompensa.objects.filter(usuario=None, puntos_necesarios__lte=usuario.puntos)

    # Obtener recompensas potenciales para el nivel actual del usuario
    recompensas_potenciales = recompensas_por_nivel.get(nivel_actual, [])

    return render(request, 'gamificacion/recompensas_disponibles.html', {
        'recompensas_disponibles': recompensas_disponibles,
        'recompensas_potenciales': recompensas_potenciales,
        'nivel_actual': nivel_actual,
    })

@login_required
def perfil_cliente(request):
    usuario = request.user

    if usuario.rol.nombre != "cliente":
        messages.error(request, "Acceso denegado.")
        return redirect("home")

    # Calcular progreso y notificaciones
    usuario.verificar_y_actualizar_nivel_cliente()
    puntos_restantes = usuario.calcular_proximo_nivel_cliente() - usuario.puntos_cliente
    progreso_nivel = (usuario.puntos_cliente / usuario.calcular_proximo_nivel_cliente()) * 100
    retos = RetoCliente.objects.filter(cliente=usuario, cumplido=False)

    return render(request, "gamificacion/perfil_cliente.html", {
        "usuario": usuario,
        "puntos_restantes": puntos_restantes,
        "progreso_nivel": round(progreso_nivel, 2),  # Redondear para mejor visualización
        "retos": retos,
    })

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

@login_required
def retos_disponibles(request):
    usuario = request.user
    if usuario.rol.nombre != "tecnico":
        messages.error(request, "Acceso denegado.")
        return redirect("home")

    asignar_retos_dinamicos(usuario)

    retos_pendientes = Reto.objects.exclude(retousuario__usuario=usuario, retousuario__cumplido=True)
    retos_completados = RetoUsuario.objects.filter(usuario=usuario, cumplido=True).select_related('reto')

    total_retos = retos_pendientes.count() + retos_completados.count()
    progreso_retos = round((retos_completados.count() / total_retos) * 100, 2) if total_retos > 0 else 0

    return render(request, 'gamificacion/retos_disponibles.html', {
        'retos_pendientes': retos_pendientes,
        'retos_completados': retos_completados,
        'progreso_retos': progreso_retos,
    })


@login_required
def lista_retos(request):

    usuario = request.user

    # Validar si el usuario tiene rol de administrador
    if usuario.rol.nombre != "administrador":
        messages.error(request, "Acceso denegado.")
        return redirect("home")


    retos = Reto.objects.all()
    return render(request, 'gamificacion/lista_retos.html', {'retos': retos})


@login_required
def crear_reto(request):

    usuario = request.user

    # Validar si el usuario tiene rol de administrador
    if usuario.rol.nombre != "administrador":
        messages.error(request, "Acceso denegado.")
        return redirect("home")

    if request.method == 'POST':
        form = RetoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Reto creado con éxito.")
            return redirect('lista_retos')
    else:
        form = RetoForm()
    return render(request, 'gamificacion/crear_reto.html', {'form': form})


@login_required
def editar_reto(request, reto_id):

    usuario = request.user

    # Validar si el usuario tiene rol de administrador
    if usuario.rol.nombre != "administrador":
        messages.error(request, "Acceso denegado.")
        return redirect("home")

    reto = get_object_or_404(Reto, id=reto_id)
    if request.method == 'POST':
        form = RetoForm(request.POST, instance=reto)
        if form.is_valid():
            form.save()
            messages.success(request, "Reto actualizado con éxito.")
            return redirect('lista_retos')
    else:
        form = RetoForm(instance=reto)
    return render(request, 'gamificacion/editar_reto.html', {'form': form})


@login_required
def eliminar_reto(request, reto_id):

    usuario = request.user

    # Validar si el usuario tiene rol de administrador
    if usuario.rol.nombre != "administrador":
        messages.error(request, "Acceso denegado.")
        return redirect("home")

    reto = get_object_or_404(Reto, id=reto_id)
    reto.delete()
    messages.success(request, "Reto eliminado con éxito.")
    return redirect('lista_retos')

# CRUD para Medallas (solo admin)
@login_required
def lista_medallas(request):

    usuario = request.user

    # Validar si el usuario tiene rol de administrador
    if usuario.rol.nombre != "administrador":
        messages.error(request, "Acceso denegado.")
        return redirect("home")

    medallas = Medalla.objects.all()
    return render(request, 'gamificacion/lista_medallas.html', {'medallas': medallas})


@login_required
def crear_medalla(request):

    usuario = request.user

    # Validar si el usuario tiene rol de administrador
    if usuario.rol.nombre != "administrador":
        messages.error(request, "Acceso denegado.")
        return redirect("home")

    if request.method == 'POST':
        form = MedallaForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Medalla creada con éxito.")
            return redirect('lista_medallas')
    else:
        form = MedallaForm()
    return render(request, 'gamificacion/crear_medalla.html', {'form': form})


@login_required
def editar_medalla(request, medalla_id):

    usuario = request.user

    # Validar si el usuario tiene rol de administrador
    if usuario.rol.nombre != "administrador":
        messages.error(request, "Acceso denegado.")
        return redirect("home")

    medalla = get_object_or_404(Medalla, id=medalla_id)
    if request.method == 'POST':
        form = MedallaForm(request.POST, request.FILES, instance=medalla)
        if form.is_valid():
            form.save()
            messages.success(request, "Medalla actualizada con éxito.")
            return redirect('lista_medallas')
    else:
        form = MedallaForm(instance=medalla)
    return render(request, 'gamificacion/editar_medalla.html', {'form': form})


@login_required
def eliminar_medalla(request, medalla_id):

    usuario = request.user

    # Validar si el usuario tiene rol de administrador
    if usuario.rol.nombre != "administrador":
        messages.error(request, "Acceso denegado.")
        return redirect("home")

    medalla = get_object_or_404(Medalla, id=medalla_id)
    medalla.delete()
    messages.success(request, "Medalla eliminada con éxito.")
    return redirect('lista_medallas')
