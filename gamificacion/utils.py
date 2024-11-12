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
            # No additional points for a 1-star rating

        # Optional: Additional points for positive comments
        if servicio.comentario_cliente and "excelente" in servicio.comentario_cliente.lower():
            puntos_servicio += 5  # e.g., bonus points for a positive comment

        # Register points obtained for this service
        RegistroPuntos.objects.create(
            usuario=usuario,
            puntos_obtenidos=puntos_servicio,
            descripcion="Servicio completado con calificación"
        )
        puntos_totales += puntos_servicio

    # Update user's total points
    usuario.puntos += puntos_totales
    usuario.save()

    return usuario.puntos

def verificar_retos(usuario):
    """
    Verifica y actualiza los retos completados por un usuario en función de sus puntos.
    """
    retos = Reto.objects.all()
    for reto in retos:
        if usuario.puntos >= reto.requisito:
            reto_usuario, created = RetoUsuario.objects.get_or_create(usuario=usuario, reto=reto)
            if not reto_usuario.cumplido:
                reto_usuario.cumplido = True
                reto_usuario.fecha_completado = timezone.now()
                reto_usuario.save()
                RegistroPuntos.objects.create(usuario=usuario, puntos_obtenidos=reto.puntos_otorgados, descripcion=f'Reto "{reto.nombre}" completado')

def asignar_medalla(usuario):
    medallas = Medalla.objects.all()
    for medalla in medallas:
        if usuario.puntos >= medalla.puntos_necesarios and not usuario.medallas.filter(id=medalla.id).exists():
            usuario.medallas.add(medalla)
            RegistroPuntos.objects.create(usuario=usuario, puntos_obtenidos=0, descripcion=f"Medalla '{medalla.nombre}' otorgada")
    usuario.save()