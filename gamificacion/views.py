from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Avg, F, Count
from django import forms
from django.contrib import messages
import json
from django.utils.timezone import now
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt

from ServiceTrack.models import Usuario, Medalla, Reto, RegistroPuntos, RetoUsuario, Guia, ObservacionIncidente, \
    Servicio, Recompensa, Temporada
from .decorators import validar_temporada_activa
from .forms import GuiaForm, ObservacionIncidenteForm, RetoForm, MedallaForm, TemporadaForm, RecompensaForm
from .utils import (
    otorgar_puntos_por_servicio,
    verificar_y_asignar_medallas_y_retos,
    generar_recomendaciones_para_tecnico,
    asignar_retos_dinamicos,
    otorgar_experiencia,
    generar_recomendaciones_con_ia,
    verificar_y_asignar_recompensas,
)
from .notifications import notificar_tecnico, notificar_tecnico_con_animacion

def es_administrador(usuario):
    return usuario.is_authenticated and usuario.rol.nombre == "administrador"

@login_required
@user_passes_test(es_administrador)
def administrar_gamificacion(request):
    """
    Vista principal para administrar la gamificación.
    """
    usuarios = Usuario.objects.all()
    temporadas = Temporada.objects.all()
    retos = Reto.objects.all()
    recompensas = Recompensa.objects.all()
    medallas = Medalla.objects.all()

    if request.method == "POST":
        # Proceso de CRUD dinámico
        action = request.POST.get("action")
        if action == "crear_temporada":
            form = TemporadaForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Temporada creada con éxito.")
        elif action == "editar_temporada":
            temporada_id = request.POST.get("temporada_id")
            temporada = get_object_or_404(Temporada, id=temporada_id)
            form = TemporadaForm(request.POST, instance=temporada)
            if form.is_valid():
                form.save()
                messages.success(request, "Temporada actualizada con éxito.")
        elif action == "eliminar_temporada":
            temporada_id = request.POST.get("temporada_id")
            Temporada.objects.filter(id=temporada_id).delete()
            messages.success(request, "Temporada eliminada con éxito.")
        elif action == "crear_reto":
            form = RetoForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Reto creado con éxito.")
        elif action == "editar_reto":
            reto_id = request.POST.get("reto_id")
            reto = get_object_or_404(Reto, id=reto_id)
            form = RetoForm(request.POST, instance=reto)
            if form.is_valid():
                form.save()
                messages.success(request, "Reto actualizado con éxito.")
        elif action == "eliminar_reto":
            reto_id = request.POST.get("reto_id")
            Reto.objects.filter(id=reto_id).delete()
            messages.success(request, "Reto eliminado con éxito.")
        elif action == "crear_recompensa":
            form = RecompensaForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Recompensa creada con éxito.")
        elif action == "editar_recompensa":
            recompensa_id = request.POST.get("recompensa_id")
            recompensa = get_object_or_404(Recompensa, id=recompensa_id)
            form = RecompensaForm(request.POST, instance=recompensa)
            if form.is_valid():
                form.save()
                messages.success(request, "Recompensa actualizada con éxito.")
        elif action == "eliminar_recompensa":
            recompensa_id = request.POST.get("recompensa_id")
            Recompensa.objects.filter(id=recompensa_id).delete()
            messages.success(request, "Recompensa eliminada con éxito.")
        elif action == "crear_medalla":
            form = MedallaForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                messages.success(request, "Medalla creada con éxito.")
        elif action == "editar_medalla":
            medalla_id = request.POST.get("medalla_id")
            medalla = get_object_or_404(Medalla, id=medalla_id)
            form = MedallaForm(request.POST, request.FILES, instance=medalla)
            if form.is_valid():
                form.save()
                messages.success(request, "Medalla actualizada con éxito.")
        elif action == "eliminar_medalla":
            medalla_id = request.POST.get("medalla_id")
            Medalla.objects.filter(id=medalla_id).delete()
            messages.success(request, "Medalla eliminada con éxito.")

        return redirect("administrar_gamificacion")

    return render(request, "gamificacion/admin_gamificacion.html", {
        "usuarios": usuarios,
        "temporadas": temporadas,
        "retos": retos,
        "recompensas": recompensas,
        "medallas": medallas,
        "temporada_form": TemporadaForm(),
        "reto_form": RetoForm(),
        "recompensa_form": RecompensaForm(),
        "medalla_form": MedallaForm(),
    })


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
@validar_temporada_activa
def perfil_gamificacion(request):
    usuario = request.user

    # Validación de acceso
    if usuario.rol.nombre != "tecnico":
        messages.error(request, "Acceso denegado.")
        return redirect("home")

    # Obtener la temporada actual
    temporada_actual = Temporada.obtener_temporada_actual()
    if not temporada_actual:
        messages.warning(request, "No hay una temporada activa en este momento.")
        return redirect("home")

    # Obtener retos asociados al nivel y temporada actual
    retos_usuario = RetoUsuario.objects.filter(
        usuario=usuario,
        reto__nivel=usuario.nivel,
        reto__temporada=temporada_actual
    )

    # Actualizar progreso de todos los retos
    for reto_usuario in retos_usuario:
        reto_usuario.actualizar_progreso()
        reto_usuario.verificar_cumplimiento()

    # Calcular número de retos cumplidos y el total de retos
    retos_completados = retos_usuario.filter(cumplido=True).count()
    total_retos_nivel = retos_usuario.count()

    # Calcular progreso basado en retos cumplidos
    progreso_nivel = (
        round((retos_completados / total_retos_nivel) * 100, 2)
        if total_retos_nivel > 0 else 0
    )

    # Sincronizar experiencia basada en retos cumplidos
    experiencia_total = sum(
        reto_usuario.reto.puntos_otorgados
        for reto_usuario in retos_usuario if reto_usuario.cumplido
    )

    if usuario.experiencia < experiencia_total:
        usuario.experiencia = experiencia_total
        usuario.save()

    # Convertir experiencia acumulada a puntos y actualizar puntos totales
    puntos_obtenidos = usuario.convertir_experiencia_a_puntos()

    # Verificar y asignar medallas y retos de la temporada actual
    animaciones = verificar_y_asignar_medallas_y_retos(usuario)

    # Filtrar medallas asociadas al nivel actual y a la temporada actual
    medallas_nivel = Medalla.objects.filter(
        retos_asociados__nivel=usuario.nivel,
        temporada=temporada_actual
    ).distinct()
    medallas_usuario = usuario.medallas.all()

    # Obtener los retos disponibles del nivel actual y de la temporada actual
    retos_disponibles = RetoUsuario.objects.filter(
        usuario=usuario,
        cumplido=False,
        reto__nivel=usuario.nivel,
        reto__temporada=temporada_actual
    ).select_related('reto')[:3]

    # Generar enlaces para redirigir a la lista de servicios según el reto
    for reto_usuario in retos_disponibles:
        reto_usuario.servicios_url = f"/servicios/tecnico_services/"

    # Calcular el progreso de medallas
    total_medallas = medallas_nivel.count()
    progreso_medallas = (
        round((medallas_usuario.filter(id__in=medallas_nivel).count() / total_medallas) * 100, 2)
        if total_medallas > 0 else 0
    )

    # Calcular el promedio de calificaciones de la temporada actual
    calificacion_promedio = usuario.calificacion_promedio_temporada(temporada_actual)

    # Sincronizar la calificación promedio del usuario
    if usuario.calificacion_promedio != calificacion_promedio:
        usuario.calificacion_promedio = calificacion_promedio
        usuario.save()

    # Obtener el total de puntos obtenidos en la temporada
    puntos_temporada = usuario.puntos_en_temporada(temporada_actual)

    # Obtener los servicios completados dentro de la temporada
    servicios_temporada = usuario.servicios_en_temporada(temporada_actual).count()

    # Generar recomendaciones personalizadas basadas en el rendimiento
    recomendaciones = generar_recomendaciones_con_ia(usuario)

    # Renderizar la página de perfil gamificado
    return render(request, "gamificacion/perfil_gamificacion.html", {
        "usuario": usuario,
        "temporada_actual": temporada_actual,
        "medallas_nivel": medallas_nivel,
        "medallas_usuario": medallas_usuario,
        "progreso_medallas": progreso_medallas,
        "calificacion_promedio": round(calificacion_promedio, 2),
        "progreso_nivel": progreso_nivel,  # Basado en retos cumplidos
        "retos_completados": retos_completados,  # Número de retos completados
        "total_retos_nivel": total_retos_nivel,  # Total de retos del nivel actual
        "retos_disponibles": retos_disponibles,
        "puntos_temporada": puntos_temporada,  # Puntos acumulados en la temporada actual
        "servicios_temporada": servicios_temporada,  # Número de servicios completados en la temporada
        "recomendaciones": recomendaciones,
        "animaciones": animaciones,
        "puntos_obtenidos": puntos_obtenidos,  # Puntos obtenidos al convertir experiencia
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
@validar_temporada_activa
def explorar_retos(request):
    usuario = request.user

    if not hasattr(usuario, 'rol') or usuario.rol.nombre != "tecnico":
        messages.error(request, "Acceso denegado.")
        return redirect("home")

    # Asegúrate de asignar retos si aún no lo has hecho
    asignar_retos_dinamicos(usuario)

    # Consultar retos pendientes y completados
    retos_pendientes = RetoUsuario.objects.filter(
        usuario=usuario,
        cumplido=False,
        reto__nivel=usuario.nivel  # Solo del nivel actual
    ).select_related('reto')

    retos_completados = RetoUsuario.objects.filter(
        usuario=usuario,
        cumplido=True,
        reto__nivel=usuario.nivel  # Solo del nivel actual
    ).select_related('reto')

    # Generar enlaces para los retos pendientes
    for reto_usuario in retos_pendientes:
        reto_usuario.servicios_url = f"/servicios/tecnico_services/"

    # Calcular progreso general de los retos
    total_retos = retos_pendientes.count() + retos_completados.count()
    progreso_retos = round((retos_completados.count() / total_retos) * 100, 2) if total_retos > 0 else 0

    return render(request, 'gamificacion/explorar_retos.html', {
        'usuario': usuario,
        'retos_pendientes': retos_pendientes,
        'retos_completados': retos_completados,
        'progreso_retos': progreso_retos,
    })

@login_required
@validar_temporada_activa
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
@validar_temporada_activa
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
@validar_temporada_activa
def recompensas_disponibles(request):
    """
    Muestra las recompensas disponibles, reclamadas y ya redimidas con descripciones completas y visualización mejorada.
    """
    usuario = request.user
    temporada_actual = Temporada.obtener_temporada_actual()

    if not temporada_actual:
        messages.warning(request, "No hay una temporada activa en este momento.")
        return redirect("home")

    # Verificar cantidad de retos cumplidos por el usuario en la temporada actual
    retos_cumplidos = RetoUsuario.objects.filter(
        usuario=usuario,
        cumplido=True,
        reto__temporada=temporada_actual
    ).count()

    # Verificar y asignar recompensas basadas en retos cumplidos dentro de la temporada
    verificar_y_asignar_recompensas(usuario, temporada_actual)

    # Obtener recompensas redimidas y disponibles
    recompensas_redimidas = Recompensa.objects.filter(
        usuario=usuario,
        redimido=True,
        temporada=temporada_actual
    ).count()

    recompensas_disponibles = Recompensa.objects.filter(
        usuario=usuario,
        redimido=False,
        temporada=temporada_actual
    )

    # Limitar recompensas disponibles según retos cumplidos menos redimidas
    limite_recompensas = retos_cumplidos - recompensas_redimidas
    recompensas_permitidas = recompensas_disponibles[:limite_recompensas]

    return render(request, 'gamificacion/recompensas_disponibles.html', {
        'recompensas_disponibles': recompensas_permitidas,
        'recompensas_redimidas': Recompensa.objects.filter(
            usuario=usuario,
            redimido=True,
            temporada=temporada_actual
        ),
        'nivel_actual': usuario.nivel,
    })

@csrf_exempt
@login_required
def redimir_recompensa(request):
    """
    Permite al usuario redimir una recompensa específica y resta los puntos necesarios.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            recompensa_id = data.get("recompensa_id")
            recompensa = get_object_or_404(Recompensa, id=recompensa_id, usuario=request.user)

            if recompensa.redimido:
                return JsonResponse({"success": False, "error": "La recompensa ya ha sido redimida."})

            # Verificar retos cumplidos y redimidos
            retos_cumplidos = RetoUsuario.objects.filter(
                usuario=request.user,
                cumplido=True,
                reto__temporada=recompensa.temporada
            ).count()

            recompensas_redimidas = Recompensa.objects.filter(
                usuario=request.user,
                redimido=True,
                temporada=recompensa.temporada
            ).count()

            if recompensas_redimidas >= retos_cumplidos:
                return JsonResponse({"success": False, "error": "No puedes redimir más recompensas sin completar más retos."})

            if request.user.puntos < recompensa.puntos_necesarios:
                return JsonResponse({"success": False, "error": "No tienes suficientes puntos para redimir esta recompensa."})

            # Procesar redención
            recompensa.redimido = True
            recompensa.save()

            # Restar los puntos necesarios
            request.user.puntos -= recompensa.puntos_necesarios
            request.user.save()

            # Registrar la redención en los logs
            RegistroPuntos.objects.create(
                usuario=request.user,
                puntos_obtenidos=-recompensa.puntos_necesarios,
                descripcion=f"Redimiste la recompensa: {recompensa.descripcion}"
            )

            # Datos para la animación y actualización en tiempo real
            respuesta = {
                "success": True,
                "mensaje": {
                    "tipo": recompensa.tipo,
                    "descripcion": recompensa.descripcion,
                    "valor": recompensa.valor,
                    "icono": "fas fa-check-circle",
                }
            }

            return JsonResponse(respuesta)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Método no permitido."})


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
@validar_temporada_activa
def retos_disponibles(request):
    usuario = request.user

    if usuario.rol.nombre != "tecnico":
        messages.error(request, "Acceso denegado.")
        return redirect("home")

    # Obtener la temporada actual
    temporada_actual = Temporada.obtener_temporada_actual()
    if not temporada_actual:
        messages.warning(request, "No hay una temporada activa en este momento.")
        return redirect("home")

    # Consultar retos pendientes y completados dentro de la temporada actual
    retos_pendientes = RetoUsuario.objects.filter(
        usuario=usuario,
        cumplido=False,
        reto__nivel=usuario.nivel,
        reto__temporada=temporada_actual
    ).select_related('reto')

    retos_cumplidos = RetoUsuario.objects.filter(
        usuario=usuario,
        cumplido=True,
        reto__nivel=usuario.nivel,
        reto__temporada=temporada_actual
    ).select_related('reto')

    # Generar enlaces para los retos pendientes
    for reto_usuario in retos_pendientes:
        reto_usuario.servicios_url = f"/servicios/tecnico_services/"

    # Calcular progreso general de retos
    total_retos = retos_pendientes.count() + retos_cumplidos.count()
    progreso_retos = round((retos_cumplidos.count() / total_retos) * 100, 2) if total_retos > 0 else 0

    return render(request, 'gamificacion/retos_disponibles.html', {
        'retos_pendientes': retos_pendientes,
        'retos_cumplidos': retos_cumplidos,
        'progreso_retos': progreso_retos,
    })


