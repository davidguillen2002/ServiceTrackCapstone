# ServiceTrack/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from ServiceTrack.models import Servicio
from gamificacion.utils import actualizar_puntos_usuario, asignar_medalla

@receiver(post_save, sender=Servicio)
def actualizar_gamificacion(sender, instance, **kwargs):
    if instance.fecha_fin:  # Solo si el servicio ha sido completado
        actualizar_puntos_usuario(instance.tecnico)
        asignar_medalla(instance.tecnico)