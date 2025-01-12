from django.core.management.base import BaseCommand
from gamificacion.utils import finalizar_temporada

class Command(BaseCommand):
    help = "Finaliza la temporada activa, registra estadísticas y reinicia los puntos."

    def handle(self, *args, **kwargs):
        finalizar_temporada()
        self.stdout.write(self.style.SUCCESS("La temporada actual ha sido finalizada y se ha creado una nueva temporada."))