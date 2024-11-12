# ServiceTrack/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from ServiceTrack.models import Servicio
from gamificacion.utils import otorgar_puntos_por_servicio, verificar_retos, asignar_medalla

@receiver(post_save, sender=Servicio)
def actualizar_gamificacion(sender, instance, **kwargs):
    if instance.estado == 'completado' and instance.fecha_fin:  # Trigger only when the service is marked completed
        otorgar_puntos_por_servicio(instance.tecnico)
        verificar_retos(instance.tecnico)
        asignar_medalla(instance.tecnico)