import json

import pandas as pd
from django.db.models import Count, Min, Sum
from ServiceTrack.models import Usuario, Servicio, Reto, RetoUsuario, RegistroPuntos, Medalla, ObservacionIncidente
from django.utils.timezone import now
from .notifications import notificar_tecnico, notificar_tecnico_con_animacion
import joblib
import os

def generar_recomendaciones_con_ia(tecnico):
    """
    Genera recomendaciones personalizadas para un técnico utilizando un modelo de aprendizaje automático.
    """
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    ruta_modelo = os.path.join(BASE_DIR, "modelo_recomendaciones.pkl")
    ruta_mapping = os.path.join(BASE_DIR, "label_mapping.json")

    try:
        # Cargar el modelo y el mapeo de etiquetas
        modelo = joblib.load(ruta_modelo)
        with open(ruta_mapping, "r") as f:
            label_mapping = json.load(f)
    except Exception as e:
        print(f"Error al cargar el modelo o el mapeo: {e}")
        return ["Error al generar recomendaciones con IA."]

    # Calcular puntos totales del técnico
    puntos_totales = RegistroPuntos.objects.filter(usuario=tecnico).aggregate(
        total=Sum('puntos_obtenidos')
    )['total'] or 0

    # Crear el DataFrame con las columnas en el mismo orden que en el entrenamiento
    columnas_modelo = [
        "nivel", "experiencia", "puntos", "calificacion_promedio",
        "servicios_completados", "incidentes_reportados", "tiempo_promedio_horas", "puntos_totales"
    ]

    datos_tecnico = pd.DataFrame([{
        "nivel": tecnico.nivel,
        "experiencia": tecnico.experiencia,
        "puntos": tecnico.puntos,
        "calificacion_promedio": tecnico.calificacion_promedio or 0,
        "servicios_completados": tecnico.tecnico_servicios.filter(estado="completado").count(),
        "incidentes_reportados": ObservacionIncidente.objects.filter(servicio__tecnico=tecnico).count(),
        "tiempo_promedio_horas": tecnico.calcular_promedio_tiempo_servicio() or 0,
        "puntos_totales": puntos_totales,
    }], columns=columnas_modelo)

    try:
        # Generar predicción
        prediccion = modelo.predict(datos_tecnico)
        etiqueta_prediccion = int(prediccion[0])  # Convertir la predicción a entero

        # Determinar retos completados y pendientes del nivel actual
        retos_cumplidos = RetoUsuario.objects.filter(usuario=tecnico, cumplido=True, reto__nivel=tecnico.nivel).count()
        retos_disponibles = RetoUsuario.objects.filter(usuario=tecnico, reto__nivel=tecnico.nivel).count()

        # Generar texto según retos cumplidos y disponibles
        if retos_cumplidos >= 2:
            texto_recomendacion = "¡Estás avanzando rápidamente! Considera asumir retos más desafiantes."
        elif retos_cumplidos == 1:
            texto_recomendacion = "Estás en camino, completa otro reto para desbloquear beneficios adicionales."
        else:
            texto_recomendacion = "Aún tienes retos pendientes. ¡Empieza con uno simple para acumular experiencia rápidamente!"

    except ValueError as ve:
        print(f"Error al mapear la etiqueta de predicción: {ve}")
        texto_recomendacion = "Revisión manual requerida."
    except Exception as e:
        print(f"Error al generar predicciones: {e}")
        return ["Error al generar recomendaciones con IA."]

    # Generar recomendaciones personalizadas para retos del nivel actual
    retos_pendientes = RetoUsuario.objects.filter(
        usuario=tecnico,
        cumplido=False,
        reto__nivel=tecnico.nivel  # Filtrar retos solo del nivel actual
    ).select_related('reto')

    recomendaciones = []

    # Recomendaciones basadas en desempeño
    if tecnico.calificacion_promedio and tecnico.calificacion_promedio < 4:
        recomendaciones.append("Trabaja en mejorar tus calificaciones para alcanzar un promedio de 4 o más.")
    elif tecnico.calificacion_promedio and tecnico.calificacion_promedio >= 4:
        recomendaciones.append("¡Excelente! Mantén tus calificaciones altas para destacar aún más.")

    if tecnico.puntos < 500:
        recomendaciones.append("Acumula más puntos completando servicios con alta calidad.")
    else:
        recomendaciones.append("¡Impresionante! Estás acumulando puntos rápidamente. Considera apoyar a otros técnicos.")

    # Recomendaciones basadas en retos disponibles
    if retos_disponibles > 0:
        recomendaciones.append(f"Tienes {retos_disponibles} retos disponibles. Selecciona uno para progresar.")
    else:
        recomendaciones.append("¡Has completado todos tus retos disponibles! Considera enfocarte en nuevas metas.")

    # Agregar recomendaciones específicas para retos pendientes
    for reto in retos_pendientes:
        progreso = reto.progreso or 0  # Manejar progreso nulo
        try:
            if progreso < reto.reto.valor_objetivo / 2:
                recomendaciones.append(
                    f"Enfócate en el reto '{reto.reto.nombre}', aún puedes avanzar significativamente."
                )
            else:
                recomendaciones.append(
                    f"Estás cerca de completar el reto '{reto.reto.nombre}'. ¡No te detengas ahora!"
                )
        except AttributeError as e:
            print(f"Error al procesar el reto '{reto.reto.nombre}': {e}")
            recomendaciones.append(f"Considera revisar el reto '{reto.reto.nombre}'.")

    # Añadir la recomendación general generada
    recomendaciones.append(texto_recomendacion)

    return recomendaciones


def otorgar_puntos_por_servicio(usuario):
    """
    Otorga puntos por servicios completados no procesados. Ajusta los puntos otorgados
    para evitar un avance excesivo en niveles.
    """
    servicios_completados = usuario.tecnico_servicios.filter(estado='completado').exclude(
        id__in=RegistroPuntos.objects.filter(usuario=usuario).values_list('servicio_id', flat=True)
    )

    puntos_totales = 0
    registros = []

    for servicio in servicios_completados:
        # Calcular puntos otorgados por el servicio
        puntos_base = 10  # Puntos iniciales por completar un servicio
        puntos_extra = max(0, (servicio.calificacion or 0) - 3) * 5  # Puntos extra por calificación mayor a 3
        puntos_servicio = puntos_base + puntos_extra

        # Validar que los puntos no excedan lo necesario para completar el nivel actual
        experiencia_requerida = usuario.calcular_experiencia_nivel_siguiente()
        if usuario.puntos + puntos_servicio > experiencia_requerida:
            puntos_servicio = experiencia_requerida - usuario.puntos

        puntos_totales += puntos_servicio

        # Registrar los puntos obtenidos
        registros.append(RegistroPuntos(
            usuario=usuario,
            servicio=servicio,
            puntos_obtenidos=puntos_servicio,
            descripcion=f"Servicio {servicio.id} completado"
        ))

    # Registrar los puntos y guardar cambios
    RegistroPuntos.objects.bulk_create(registros)
    usuario.puntos += puntos_totales
    usuario.save()

    return puntos_totales

from django.utils.timezone import now
from ServiceTrack.models import RegistroPuntos, RetoUsuario, Medalla
from gamificacion.notifications import notificar_tecnico, notificar_tecnico_con_animacion


def verificar_y_asignar_medallas_y_retos(usuario):
    """
    Verifica si el usuario cumple con los requisitos para medallas y sincroniza retos asociados,
    asegurándose de validar correctamente los criterios para medallas y retos.
    """
    medallas = Medalla.objects.all()
    animaciones = []  # Lista para acumular las animaciones que se enviarán al frontend

    for medalla in medallas:
        # Verificar si el usuario cumple con los requisitos de la medalla
        retos_cumplidos = all(
            RetoUsuario.objects.filter(usuario=usuario, reto=reto, cumplido=True).exists()
            for reto in medalla.retos_asociados.all()
        )
        if (
            retos_cumplidos
            and usuario.puntos >= medalla.puntos_necesarios
            and usuario.nivel >= medalla.nivel_requerido
            and not usuario.medallas.filter(id=medalla.id).exists()
        ):
            usuario.medallas.add(medalla)
            RegistroPuntos.objects.create(
                usuario=usuario,
                puntos_obtenidos=0,  # No otorgar puntos adicionales al asignar medallas
                descripcion=f"Medalla '{medalla.nombre}' otorgada"
            )

            # Crear notificación para el técnico con animación
            notificar_tecnico_con_animacion(
                usuario,
                f"¡Has ganado la medalla '{medalla.nombre}'! 🎉",
                tipo="success",
                animacion="bounceIn"
            )
            animaciones.append({
                "tipo": "success",
                "mensaje": f"¡Has ganado la medalla '{medalla.nombre}'! 🎉",
                "animacion": "bounceIn",
            })

            # Marcar retos asociados como cumplidos si corresponde
            for reto in medalla.retos_asociados.all():
                reto_usuario = RetoUsuario.objects.filter(usuario=usuario, reto=reto).first()
                if reto_usuario and not reto_usuario.cumplido:
                    reto_usuario.cumplido = True
                    reto_usuario.progreso = 100
                    reto_usuario.fecha_completado = now()
                    reto_usuario.save()

    # Verificar progreso de retos pendientes
    retos = RetoUsuario.objects.filter(usuario=usuario, cumplido=False)
    for reto_usuario in retos:
        reto_usuario.actualizar_progreso()
        if reto_usuario.progreso >= 100 and not reto_usuario.cumplido:
            reto_usuario.cumplido = True
            reto_usuario.fecha_completado = now()
            reto_usuario.save()

            # Crear notificación para el técnico con animación
            notificar_tecnico_con_animacion(
                usuario,
                f"¡Has completado el reto '{reto_usuario.reto.nombre}'! 🏆",
                tipo="info",
                animacion="rubberBand"
            )
            animaciones.append({
                "tipo": "info",
                "mensaje": f"¡Has completado el reto '{reto_usuario.reto.nombre}'! 🏆",
                "animacion": "rubberBand",
            })

            # Otorgar puntos por el reto completado
            usuario.puntos += reto_usuario.reto.puntos_otorgados
            RegistroPuntos.objects.create(
                usuario=usuario,
                puntos_obtenidos=reto_usuario.reto.puntos_otorgados,
                descripcion=f"Reto completado: {reto_usuario.reto.nombre}"
            )

    # Evitar exceso de puntos y ajustar niveles si corresponde
    experiencia_requerida = usuario.calcular_experiencia_nivel_siguiente()
    while usuario.experiencia >= experiencia_requerida and usuario.nivel < 5:
        usuario.experiencia -= experiencia_requerida
        usuario.nivel += 1
        experiencia_requerida = usuario.calcular_experiencia_nivel_siguiente()

        # Notificar sobre el nuevo nivel alcanzado
        notificar_tecnico_con_animacion(
            usuario,
            f"¡Felicidades {usuario.nombre}, has alcanzado el nivel {usuario.nivel}! 🎉",
            tipo="info",
            animacion="tada"
        )
        animaciones.append({
            "tipo": "info",
            "mensaje": f"¡Felicidades {usuario.nombre}, has alcanzado el nivel {usuario.nivel}! 🎉",
            "animacion": "tada",
        })

    # Ajustar experiencia sobrante si se alcanza el nivel máximo
    if usuario.nivel >= 5:
        usuario.experiencia = 0

    usuario.save()
    return animaciones  # Devolver la lista de animaciones para el frontend

def generar_recomendaciones_para_tecnico(tecnico):
    """
    Genera recomendaciones personalizadas para un técnico basado en su desempeño.
    """
    recomendaciones = []

    # Calcular tiempos promedio
    promedio_tiempo = tecnico.calcular_promedio_tiempo_servicio()
    if promedio_tiempo:
        if promedio_tiempo > 7:
            recomendaciones.append("Reduce tu tiempo promedio de servicio para mejorar la eficiencia.")
        elif promedio_tiempo < 3:
            recomendaciones.append("¡Excelente! Mantén un tiempo de servicio eficiente.")
    else:
        recomendaciones.append("Aún no hay suficientes datos sobre tiempos de servicio.")

    # Revisar calificaciones bajas
    calificaciones_bajas = Servicio.objects.filter(tecnico=tecnico, calificacion__lt=3).count()
    if calificaciones_bajas > 5:
        recomendaciones.append(f"Revisa los {calificaciones_bajas} servicios con calificaciones bajas para buscar áreas de mejora.")
    elif calificaciones_bajas == 0:
        recomendaciones.append("¡Buen trabajo! No tienes servicios con calificaciones bajas.")

    # Patrones de incidentes
    incidentes = ObservacionIncidente.objects.filter(servicio__tecnico=tecnico).count()
    if incidentes > 3:
        recomendaciones.append("Analiza los incidentes frecuentes y toma medidas para prevenir futuros problemas.")
    elif incidentes == 0:
        recomendaciones.append("¡Bien hecho! No se han registrado incidentes en tus servicios.")

    # Verificar nivel de puntos
    if tecnico.puntos < 300:
        recomendaciones.append("Completa más servicios con altas calificaciones para aumentar tu puntaje.")
    elif tecnico.calificacion_promedio < 4:
        recomendaciones.append("Apunta a un promedio de calificación de 4 o más para desbloquear retos premium.")

    # Verificar retos pendientes
    retos_pendientes = RetoUsuario.objects.filter(usuario=tecnico, cumplido=False).count()
    if retos_pendientes > 0:
        recomendaciones.append(f"Tienes {retos_pendientes} retos pendientes. ¡No te olvides de completarlos!")
    else:
        recomendaciones.append("¡Excelente! Has completado todos tus retos actuales.")

    return recomendaciones

def asignar_retos_dinamicos(tecnico):
    """
    Asigna retos específicos al técnico según su nivel actual.
    """
    # Obtener los retos para el nivel actual del técnico
    retos_nivel = Reto.objects.filter(nivel=tecnico.nivel)
    print(f"Retos disponibles para nivel {tecnico.nivel}: {retos_nivel}")

    for reto in retos_nivel:
        # Crear una relación en RetoUsuario si no existe
        reto_usuario, created = RetoUsuario.objects.get_or_create(
            usuario=tecnico,
            reto=reto,
            defaults={'cumplido': False, 'progreso': 0}
        )
        if created:
            print(f"Reto asignado: {reto.nombre} al usuario {tecnico.nombre}")
        else:
            print(f"Reto ya existente: {reto.nombre} para usuario {tecnico.nombre}")

def otorgar_experiencia(usuario, cantidad):
    """
    Otorga experiencia al usuario, verifica si sube de nivel y ajusta retos asociados.
    """
    usuario.experiencia += cantidad
    while usuario.experiencia >= usuario.calcular_experiencia_nivel_siguiente():
        exceso = usuario.experiencia - usuario.calcular_experiencia_nivel_siguiente()
        usuario.nivel += 1
        usuario.experiencia = exceso
        notificar_tecnico(
            usuario=usuario,
            mensaje=f"¡Felicidades {usuario.nombre}, alcanzaste el nivel {usuario.nivel}! 🎉",
            tipo="info"
        )
        usuario.asignar_retos_por_nivel(usuario)  # Asignar retos nuevos para el nivel actual
    usuario.save()

def limpiar_duplicados_retousuario():
    """
    Elimina registros duplicados en la tabla RetoUsuario, dejando solo el más antiguo.
    También asegura que solo queden retos asignados al nivel correcto.
    """
    duplicados = (
        RetoUsuario.objects.values('usuario', 'reto')
        .annotate(total=Count('id'), min_id=Min('id'))
        .filter(total__gt=1)
    )

    for duplicado in duplicados:
        RetoUsuario.objects.filter(
            usuario_id=duplicado['usuario'],
            reto_id=duplicado['reto']
        ).exclude(id=duplicado['min_id']).delete()

    # Eliminar retos asignados a usuarios en niveles incorrectos
    for usuario in Usuario.objects.filter(rol__nombre="tecnico"):
        RetoUsuario.objects.filter(usuario=usuario).exclude(reto__nivel=usuario.nivel).delete()

