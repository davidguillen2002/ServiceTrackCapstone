# gamificacion/utils.py
from ServiceTrack.models import Usuario, Servicio
from django.db.models import Sum

def actualizar_puntos_usuario(usuario):
    """
    Actualiza los puntos acumulados del usuario basado en los servicios completados.
    """
    servicios_completados = Servicio.objects.filter(tecnico=usuario, fecha_fin__isnull=False)
    puntos_totales = servicios_completados.count() * 10  # Ejemplo: 10 puntos por servicio completado
    usuario.puntos = puntos_totales
    usuario.save()
    return usuario.puntos

def asignar_medalla(usuario):
    """
    Asigna medallas al usuario basado en logros específicos (como completar 10 servicios).
    """
    if usuario.puntos >= 100:  # Ejemplo: 100 puntos para la primera medalla
        usuario.medalla_set.create(nombre="Medalla de Excelencia", descripcion="Por completar más de 10 servicios.")
    # Agrega más lógica de medallas aquí si es necesario