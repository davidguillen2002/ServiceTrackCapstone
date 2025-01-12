from django.db.models import Avg
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
                # Experiencia y progreso de nivel
                experiencia_actual = usuario.experiencia
                experiencia_requerida = usuario.calcular_experiencia_nivel_siguiente()
                progreso_nivel = (
                    round((experiencia_actual / experiencia_requerida) * 100, 2)
                    if experiencia_requerida > 0 else 0
                )

                # Calificación promedio
                calificacion_promedio = (
                    Servicio.objects.filter(tecnico=usuario, estado="completado")
                    .aggregate(promedio=Avg("calificacion"))["promedio"]
                    or 0
                )

                # Progreso de medallas
                total_medallas = Medalla.objects.count()
                progreso_medallas = (
                    round((usuario.medallas.count() / total_medallas) * 100, 2)
                    if total_medallas > 0 else 0
                )

                # Retos completados y disponibles
                retos_disponibles = RetoUsuario.objects.filter(usuario=usuario, cumplido=False).count()
                retos_completados = RetoUsuario.objects.filter(usuario=usuario, cumplido=True).count()

                # Temporada activa
                fecha_actual = now().date()
                temporada_activa = Temporada.objects.filter(
                    fecha_inicio__lte=fecha_actual, fecha_fin__gte=fecha_actual
                ).first()

                return {
                    "usuario": usuario,
                    "experiencia_actual": experiencia_actual,
                    "experiencia_requerida": experiencia_requerida,
                    "progreso_nivel": progreso_nivel,
                    "calificacion_promedio": round(calificacion_promedio, 2),
                    "progreso_medallas": progreso_medallas,
                    "retos_disponibles": retos_disponibles,
                    "retos_completados": retos_completados,
                    "temporada_activa": temporada_activa,  # Agregado
                }
    except Exception as e:
        # Registrar errores para depuración
        print(f"Error en gamificacion_context: {e}")
        return {}

    return {}