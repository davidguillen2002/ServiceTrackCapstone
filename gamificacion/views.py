from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Avg, F, Count, OuterRef, Subquery
from django import forms
from django.contrib import messages
import json
from django.utils import timezone
from django.utils.timezone import now
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from ServiceTrack.models import Usuario, Medalla, Reto, RegistroPuntos, RetoUsuario, Guia, ObservacionIncidente, \
    Servicio, Recompensa, Temporada, RecompensaUsuario
from .decorators import validar_temporada_activa
from .forms import GuiaForm, ObservacionIncidenteForm, RetoForm, MedallaForm, TemporadaForm, RecompensaForm
from .utils import (
    otorgar_puntos_por_servicio,
    verificar_y_asignar_medallas_y_retos,
    generar_recomendaciones_para_tecnico,
    asignar_retos_dinamicos,
    otorgar_experiencia,
    generar_recomendaciones_con_ia,
    sincronizar_y_asignar_recompensas,
)
from .notifications import notificar_tecnico, notificar_tecnico_con_animacion

def es_administrador(usuario):
    return usuario.is_authenticated and usuario.rol.nombre == "administrador"

# Vista para administrar la gamificación
@login_required
@user_passes_test(es_administrador)  # Asegura que solo el personal administrativo acceda
def administrar_gamificacion(request):
    """
    Vista principal para administrar la gamificación con funcionalidad CRUD, otorgar puntos y paginación.
    Incluye soporte para procesamiento mediante AJAX.
    """

    # Paginación de datos
    def paginate_queryset(queryset, page_param, items_per_page=5):
        page = request.GET.get(page_param, 1)
        paginator = Paginator(queryset, items_per_page)
        try:
            paginated_data = paginator.page(page)
        except PageNotAnInteger:
            paginated_data = paginator.page(1)
        except EmptyPage:
            paginated_data = paginator.page(paginator.num_pages)
        return paginated_data, paginator

    # Paginación individual para cada sección
    temporadas, temporadas_paginator = paginate_queryset(
        Temporada.objects.all().order_by('-fecha_inicio'), 'temporadas_page'
    )
    retos, retos_paginator = paginate_queryset(
        Reto.objects.all().order_by('-id'), 'retos_page'
    )
    recompensas, recompensas_paginator = paginate_queryset(
        Recompensa.objects.all().order_by('-id'), 'recompensas_page'
    )
    medallas, medallas_paginator = paginate_queryset(
        Medalla.objects.all().order_by('-id'), 'medallas_page'
    )

    # Procesar formulario de otorgar puntos
    if request.method == "POST" and request.POST.get("action") == "otorgar_puntos":
        otorgar_puntos_form = OtorgarPuntosForm(request.POST)
        if otorgar_puntos_form.is_valid():
            tecnico = otorgar_puntos_form.cleaned_data["usuario"]
            puntos = otorgar_puntos_form.cleaned_data["puntos"]
            descripcion = otorgar_puntos_form.cleaned_data["descripcion"]

            tecnico.puntos += puntos
            tecnico.save()

            RegistroPuntos.objects.create(usuario=tecnico, puntos_obtenidos=puntos, descripcion=descripcion)
            messages.success(request, f"{puntos} puntos otorgados con éxito a {tecnico.nombre}.")
            return redirect("administrar_gamificacion")
        else:
            messages.error(request, "Error al otorgar puntos. Revisa los datos ingresados.")
    else:
        otorgar_puntos_form = OtorgarPuntosForm()

    # Procesar acciones CRUD dinámicas y soporte para AJAX
    if request.method == "POST" and request.POST.get("action") != "otorgar_puntos":
        action = request.POST.get("action")

        if action == "crear_temporada":
            form = TemporadaForm(request.POST)
            if form.is_valid():
                temporada = form.save()
                if request.is_ajax():
                    return JsonResponse({"success": True, "temporada": {
                        "nombre": temporada.nombre,
                        "fecha_inicio": temporada.fecha_inicio.strftime('%Y-%m-%d'),
                        "fecha_fin": temporada.fecha_fin.strftime('%Y-%m-%d')
                    }})
                messages.success(request, "Temporada creada con éxito.")
            else:
                if request.is_ajax():
                    return JsonResponse({"success": False, "errors": form.errors})
                messages.error(request, "Error al crear la temporada.")

        elif action == "eliminar_temporada":
            Temporada.objects.filter(id=request.POST.get("temporada_id")).delete()
            messages.success(request, "Temporada eliminada con éxito.")

        elif action == "crear_reto":
            form = RetoForm(request.POST)
            if form.is_valid():
                reto = form.save()
                if request.is_ajax():
                    return JsonResponse({"success": True, "reto": {
                        "nombre": reto.nombre,
                        "nivel": reto.nivel,
                        "temporada": reto.temporada.nombre
                    }})
                messages.success(request, "Reto creado con éxito.")
            else:
                if request.is_ajax():
                    return JsonResponse({"success": False, "errors": form.errors})
                messages.error(request, "Error al crear el reto.")

        elif action == "eliminar_reto":
            Reto.objects.filter(id=request.POST.get("reto_id")).delete()
            messages.success(request, "Reto eliminado con éxito.")

        elif action == "crear_recompensa":
            form = RecompensaForm(request.POST)
            if form.is_valid():
                recompensa = form.save()
                if request.is_ajax():
                    return JsonResponse({"success": True, "recompensa": {
                        "descripcion": recompensa.descripcion,
                        "tipo": recompensa.tipo,
                        "temporada": recompensa.temporada.nombre
                    }})
                messages.success(request, "Recompensa creada con éxito.")
            else:
                if request.is_ajax():
                    return JsonResponse({"success": False, "errors": form.errors})
                messages.error(request, "Error al crear la recompensa.")

        elif action == "eliminar_recompensa":
            Recompensa.objects.filter(id=request.POST.get("recompensa_id")).delete()
            messages.success(request, "Recompensa eliminada con éxito.")

        elif action == "crear_medalla":
            form = MedallaForm(request.POST, request.FILES)
            if form.is_valid():
                medalla = form.save()
                if request.is_ajax():
                    return JsonResponse({"success": True, "medalla": {
                        "nombre": medalla.nombre,
                        "nivel_requerido": medalla.nivel_requerido,
                        "temporada": medalla.temporada.nombre if medalla.temporada else "Sin Temporada"
                    }})
                messages.success(request, "Medalla creada con éxito.")
            else:
                if request.is_ajax():
                    return JsonResponse({"success": False, "errors": form.errors})
                messages.error(request, "Error al crear la medalla.")

        elif action == "eliminar_medalla":
            Medalla.objects.filter(id=request.POST.get("medalla_id")).delete()
            messages.success(request, "Medalla eliminada con éxito.")

        else:
            messages.error(request, "Acción no reconocida.")
        return redirect("administrar_gamificacion")

    return render(request, "gamificacion/admin_gamificacion.html", {
        "temporadas": temporadas,
        "retos": retos,
        "recompensas": recompensas,
        "medallas": medallas,
        "temporada_form": TemporadaForm(),
        "reto_form": RetoForm(),
        "recompensa_form": RecompensaForm(),
        "medalla_form": MedallaForm(),
        "otorgar_puntos_form": otorgar_puntos_form,
        "temporadas_paginator": temporadas_paginator,
        "retos_paginator": retos_paginator,
        "recompensas_paginator": recompensas_paginator,
        "medallas_paginator": medallas_paginator,
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

    # Actualizar estadísticas del usuario (calificación promedio y servicios completados)
    usuario.actualizar_estadisticas()

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

    # Validar que el promedio esté dentro del rango de fechas de la temporada
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

# Vista para recompensas disponibles
@login_required
@validar_temporada_activa
def recompensas_disponibles(request):
    usuario = request.user
    temporada_actual = Temporada.obtener_temporada_actual()

    if not temporada_actual:
        messages.warning(request, "No hay una temporada activa en este momento.")
        return redirect("home")

    # Sincronizar y asignar recompensas específicas al usuario
    sincronizar_y_asignar_recompensas(temporada_actual, usuario)

    # Obtener recompensas disponibles para el usuario
    recompensas_disponibles = RecompensaUsuario.objects.filter(
        usuario=usuario,
        redimido=False,
        recompensa__temporada=temporada_actual
    ).select_related('recompensa')

    # Obtener recompensas ya redimidas por el usuario
    recompensas_redimidas = RecompensaUsuario.objects.filter(
        usuario=usuario,
        redimido=True,
        recompensa__temporada=temporada_actual
    ).select_related('recompensa')

    # Renderizar la vista con las recompensas disponibles y redimidas
    return render(request, 'gamificacion/recompensas_disponibles.html', {
        'recompensas_disponibles': recompensas_disponibles,
        'recompensas_redimidas': recompensas_redimidas,
        'nivel_actual': usuario.nivel,
    })


@csrf_exempt
@login_required
def redimir_recompensa(request):
    """
    Permite redimir una recompensa específica si se cumplen las condiciones.
    """
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            recompensa_usuario_id = body.get("recompensa_id")
            usuario = request.user

            # Validar si la recompensa está asignada al usuario y aún no ha sido redimida
            recompensa_usuario = RecompensaUsuario.objects.get(
                id=recompensa_usuario_id,
                usuario=usuario,
                redimido=False
            )

            # Validar si el usuario tiene suficientes puntos
            if usuario.puntos < recompensa_usuario.recompensa.puntos_necesarios:
                return JsonResponse({"success": False, "error": "No tienes suficientes puntos para redimir esta recompensa."})

            # Procesar la redención de la recompensa
            recompensa_usuario.redimido = True
            recompensa_usuario.fecha_redencion = timezone.now()
            recompensa_usuario.save()

            # Descontar los puntos del usuario
            usuario.puntos -= recompensa_usuario.recompensa.puntos_necesarios
            usuario.save()

            return JsonResponse({
                "success": True,
                "mensaje": {
                    "tipo": recompensa_usuario.recompensa.tipo,
                    "descripcion": recompensa_usuario.recompensa.descripcion,
                    "id": recompensa_usuario.id
                }
            })

        except RecompensaUsuario.DoesNotExist:
            return JsonResponse({"success": False, "error": "La recompensa no existe o ya fue redimida."})

        except Exception as e:
            return JsonResponse({"success": False, "error": f"Error inesperado: {str(e)}"})

    return JsonResponse({"success": False, "error": "Método no permitido."}, status=405)


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

def crear_temporada_ajax(request):
    if request.method == "POST":
        form = TemporadaForm(request.POST)
        if form.is_valid():
            temporada = form.save()
            return JsonResponse({
                "success": True,
                "temporada": {
                    "id": temporada.id,
                    "nombre": temporada.nombre,
                    "fecha_inicio": temporada.fecha_inicio.strftime("%Y-%m-%d"),
                    "fecha_fin": temporada.fecha_fin.strftime("%Y-%m-%d"),
                },
            })
        return JsonResponse({"success": False, "errors": form.errors})
    return JsonResponse({"success": False, "error": "Método no permitido."}, status=405)

def crear_reto_ajax(request):
    if request.method == "POST":
        form = RetoForm(request.POST)
        if form.is_valid():
            reto = form.save()
            return JsonResponse({
                "success": True,
                "reto": {
                    "id": reto.id,
                    "nombre": reto.nombre,
                    "descripcion": reto.descripcion,
                    "puntos_otorgados": reto.puntos_otorgados,
                    "criterio": reto.criterio,
                    "valor_objetivo": reto.valor_objetivo,
                },
            })
        return JsonResponse({"success": False, "errors": form.errors})
    return JsonResponse({"success": False, "error": "Método no permitido."}, status=405)

def crear_recompensa_ajax(request):
    if request.method == "POST":
        form = RecompensaForm(request.POST)
        if form.is_valid():
            recompensa = form.save()
            return JsonResponse({
                "success": True,
                "recompensa": {
                    "id": recompensa.id,
                    "tipo": recompensa.tipo,
                    "descripcion": recompensa.descripcion,
                    "valor": recompensa.valor,
                    "puntos_necesarios": recompensa.puntos_necesarios,
                },
            })
        return JsonResponse({"success": False, "errors": form.errors})
    return JsonResponse({"success": False, "error": "Método no permitido."}, status=405)

def crear_medalla_ajax(request):
    if request.method == "POST":
        form = MedallaForm(request.POST, request.FILES)
        if form.is_valid():
            medalla = form.save()
            return JsonResponse({
                "success": True,
                "medalla": {
                    "id": medalla.id,
                    "nombre": medalla.nombre,
                    "descripcion": medalla.descripcion,
                    "puntos_necesarios": medalla.puntos_necesarios,
                    "nivel_requerido": medalla.nivel_requerido,
                },
            })
        return JsonResponse({"success": False, "errors": form.errors})
    return JsonResponse({"success": False, "error": "Método no permitido."}, status=405)
