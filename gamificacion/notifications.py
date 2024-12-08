from ServiceTrack.models import Notificacion
from django.utils.timezone import now


def notificar_tecnico(usuario, mensaje, tipo="info"):
    """
    Crea una notificación para un técnico.
    """
    from ServiceTrack.models import Notificacion  # Importación local para evitar el ciclo

    Notificacion.objects.create(
        usuario=usuario,
        tipo=tipo,
        mensaje=mensaje,
        fecha_creacion=now(),
        leido=False,
    )



def notificar_tecnico_con_animacion(usuario, mensaje, tipo="info", animacion="fadeIn"):
    """
    Crea una notificación enriquecida con animación para un técnico.
    """
    from ServiceTrack.models import Notificacion  # Importación local para evitar el ciclo

    Notificacion.objects.create(
        usuario=usuario,
        tipo=tipo,
        mensaje=mensaje,
        fecha_creacion=now(),
        leido=False,
        extra_data={"animacion": animacion},  # Campo para animaciones específicas
    )


def notificar_grupo(tecnicos, mensaje, tipo="info", animacion="bounceIn"):
    """
    Envía una notificación a un grupo de técnicos.
    """
    for tecnico in tecnicos:
        Notificacion.objects.create(
            usuario=tecnico,
            tipo=tipo,
            mensaje=mensaje,
            fecha_creacion=now(),
            leido=False,
            extra_data={"animacion": animacion},
        )