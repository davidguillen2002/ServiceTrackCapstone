# ServiceTrack/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from ServiceTrack.models import Servicio
from gamificacion.utils import otorgar_puntos_por_servicio, verificar_y_asignar_medallas_y_retos

@receiver(post_save, sender=Servicio)
def actualizar_gamificacion(sender, instance, **kwargs):
    """
    Actualiza la gamificación del técnico cuando un servicio es completado.
    """
    try:
        if instance.esta_completado and instance.tecnico:
            # Otorgar puntos al técnico
            otorgar_puntos_por_servicio(instance.tecnico)
            # Verificar retos y asignar medallas asociadas
            verificar_y_asignar_medallas_y_retos(instance.tecnico)
    except Exception as e:
        # Registro del error para depuración
        print(f"Error en actualizar_gamificacion para servicio {instance.id}: {e}")