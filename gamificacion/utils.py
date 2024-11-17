from ServiceTrack.models import Usuario, Servicio, Reto, RetoUsuario, RegistroPuntos, Medalla
from django.utils import timezone

def otorgar_puntos_por_servicio(usuario):
    """
    Updates points for a technician based on completed services and client rating.
    """
    servicios_completados = Servicio.objects.filter(tecnico=usuario, estado='completado')
    puntos_totales = 0

    for servicio in servicios_completados:
        # Base points for completing the service
        puntos_servicio = 10

        # Additional points based on client rating
        if servicio.calificacion:
            if servicio.calificacion == 5:
                puntos_servicio += 10
            elif servicio.calificacion == 4:
                puntos_servicio += 7
            elif servicio.calificacion == 3:
                puntos_servicio += 5
            elif servicio.calificacion == 2:
                puntos_servicio += 2

        # Optional: Additional points for positive comments
        if servicio.comentario_cliente and "excelente" in servicio.comentario_cliente.lower():
            puntos_servicio += 5

        # Register points obtained for this service
        RegistroPuntos.objects.create(
            usuario=usuario,
            puntos_obtenidos=puntos_servicio,
            descripcion=f"Servicio {servicio.id} completado con calificación"
        )
        puntos_totales += puntos_servicio

    # Update user's total points
    usuario.puntos += puntos_totales
    usuario.save()

    return usuario.puntos


def verificar_retos(usuario):
    """
    Verifies and updates completed challenges (retos) for a user based on their points.
    """
    retos = Reto.objects.all()
    for reto in retos:
        if usuario.puntos >= reto.requisito:
            reto_usuario, created = RetoUsuario.objects.get_or_create(usuario=usuario, reto=reto)
            if not reto_usuario.cumplido:
                reto_usuario.cumplido = True
                reto_usuario.fecha_completado = timezone.now()
                reto_usuario.save()
                RegistroPuntos.objects.create(
                    usuario=usuario,
                    puntos_obtenidos=reto.puntos_otorgados,
                    descripcion=f'Reto "{reto.nombre}" completado'
                )


def asignar_medalla(usuario):
    """
    Assigns medals to a user based on their total points.
    """
    medallas = Medalla.objects.all()
    for medalla in medallas:
        if usuario.puntos >= medalla.puntos_necesarios and not usuario.medallas.filter(id=medalla.id).exists():
            usuario.medallas.add(medalla)
            RegistroPuntos.objects.create(
                usuario=usuario,
                puntos_obtenidos=0,
                descripcion=f"Medalla '{medalla.nombre}' otorgada"
            )
    usuario.save()


def generar_recomendaciones_para_tecnico(tecnico):
    recomendaciones = []

    # Análisis del tiempo promedio de servicio
    promedio_tiempo = tecnico.calcular_promedio_tiempo_servicio()
    if promedio_tiempo and promedio_tiempo > 7:
        recomendaciones.append("Reduce tu tiempo promedio de servicio para mejorar la eficiencia.")

    # Calificaciones bajas
    calificaciones_bajas = tecnico.servicios_con_baja_calificacion()
    if calificaciones_bajas > 5:
        recomendaciones.append("Revisa los servicios con calificaciones bajas y busca áreas de mejora.")

    # Patrones de incidentes
    incidentes = Servicio.objects.filter(tecnico=tecnico, observaciones__isnull=False).count()
    if incidentes > 3:
        recomendaciones.append("Analiza los incidentes frecuentes para prevenir futuros problemas.")

    # Nuevas recomendaciones basadas en desempeño general
    if tecnico.puntos < 300:
        recomendaciones.append("Completa más servicios con altas calificaciones para aumentar tu puntaje.")
    elif tecnico.calificacion_promedio < 4:
        recomendaciones.append("Apunta a un promedio de calificación de 4 o más para desbloquear retos premium.")

    return recomendaciones

def asignar_retos_dinamicos(tecnico):
    """
    Dynamically assigns challenges to a technician based on their performance data.
    """
    # Retos basados en calificaciones bajas
    if tecnico.servicios_con_baja_calificacion() > 3:
        reto, created = Reto.objects.get_or_create(
            nombre="Mejorar calificaciones",
            descripcion="Logra una calificación promedio superior a 4 en tus próximos 5 servicios.",
            puntos_otorgados=50,
            requisito=5,
        )
        if created:
            RetoUsuario.objects.create(usuario=tecnico, reto=reto, cumplido=False)

    # Retos basados en tiempo promedio alto
    promedio_tiempo = tecnico.calcular_promedio_tiempo_servicio()
    if promedio_tiempo and promedio_tiempo > 7:
        reto, created = Reto.objects.get_or_create(
            nombre="Optimizar tiempos",
            descripcion="Reduce tu tiempo promedio a menos de 7 días en los próximos 5 servicios.",
            puntos_otorgados=50,
            requisito=5,
        )
        if created:
            RetoUsuario.objects.create(usuario=tecnico, reto=reto, cumplido=False)

    # Retos personalizados por puntos acumulados
    if tecnico.puntos < 500:
        Reto.objects.get_or_create(
            nombre="Alcanza los 500 puntos",
            descripcion="Suma suficientes puntos para llegar a un total de 500.",
            puntos_otorgados=100,
            requisito=500,
        )