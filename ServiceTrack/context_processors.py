from django.db.models import Avg, Sum, Count
from ServiceTrack.models import Usuario, Servicio, Medalla, RetoUsuario, Temporada
from django.utils.timezone import now

def gamificacion_context(request):
    """
    Proporciona datos del perfil de gamificación para todas las vistas.
    """
    try:
        if request.user.is_authenticated:
            usuario = request.user
            if hasattr(usuario, 'rol') and usuario.rol.nombre == "tecnico":
                # Obtener la temporada activa
                fecha_actual = now().date()
                temporada_activa = Temporada.objects.filter(
                    fecha_inicio__lte=fecha_actual,
                    fecha_fin__gte=fecha_actual
                ).first()

                # Verificar si hay una temporada activa
                if not temporada_activa:
                    return {
                        "usuario": usuario,
                        "temporada_activa": None,
                    }

                # Sincronizar experiencia y convertirla en puntos
                puntos_obtenidos = usuario.convertir_experiencia_a_puntos()

                # Experiencia actual y progreso de nivel
                experiencia_actual = usuario.experiencia
                experiencia_requerida = usuario.calcular_experiencia_nivel_siguiente()
                progreso_nivel = (
                    round((experiencia_actual / experiencia_requerida) * 100, 2)
                    if experiencia_requerida > 0 else 0
                )

                # Calcular promedio de calificaciones dentro de la temporada activa
                servicios_temporada = usuario.servicios_en_temporada(temporada_activa)
                calificacion_promedio_temporada = servicios_temporada.aggregate(
                    promedio=Avg('calificacion')
                )['promedio'] or 0

                # Actualizar calificación promedio del usuario si es necesario
                if round(usuario.calificacion_promedio, 2) != round(calificacion_promedio_temporada, 2):
                    usuario.calificacion_promedio = round(calificacion_promedio_temporada, 2)
                    usuario.save()

                # Progreso de medallas asociadas al nivel y temporada activa
                total_medallas_nivel = Medalla.objects.filter(
                    retos_asociados__nivel=usuario.nivel,
                    temporada=temporada_activa
                ).distinct().count()
                medallas_obtenidas = usuario.medallas.filter(
                    retos_asociados__nivel=usuario.nivel,
                    temporada=temporada_activa
                ).distinct().count()
                progreso_medallas = (
                    round((medallas_obtenidas / total_medallas_nivel) * 100, 2)
                    if total_medallas_nivel > 0 else 0
                )

                # Retos cumplidos y pendientes en la temporada activa
                retos_cumplidos = RetoUsuario.objects.filter(
                    usuario=usuario,
                    cumplido=True,
                    reto__temporada=temporada_activa
                ).count()
                retos_pendientes = RetoUsuario.objects.filter(
                    usuario=usuario,
                    cumplido=False,
                    reto__temporada=temporada_activa
                ).count()

                # Puntos obtenidos dentro de la temporada
                puntos_temporada = usuario.puntos_en_temporada(temporada_activa)

                # Total de servicios completados en la temporada
                servicios_completados_temporada = servicios_temporada.filter(estado="completado").count()

                return {
                    "usuario": usuario,
                    "temporada_activa": temporada_activa,
                    "experiencia_actual": experiencia_actual,
                    "experiencia_requerida": experiencia_requerida,
                    "progreso_nivel": progreso_nivel,
                    "calificacion_promedio_temporada": round(calificacion_promedio_temporada, 2),
                    "progreso_medallas": progreso_medallas,
                    "retos_cumplidos": retos_cumplidos,
                    "retos_pendientes": retos_pendientes,
                    "puntos_temporada": puntos_temporada,
                    "servicios_completados_temporada": servicios_completados_temporada,
                    "puntos_obtenidos": puntos_obtenidos,  # Puntos convertidos de experiencia
                }
    except Exception as e:
        # Registrar errores para depuración
        print(f"Error en gamificacion_context: {e}")
        return {}

    return {}