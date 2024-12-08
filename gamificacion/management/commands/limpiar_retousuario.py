from django.core.management.base import BaseCommand
from django.db.models import Count, Min
from ServiceTrack.models import RetoUsuario

class Command(BaseCommand):
    help = "Elimina registros duplicados en la tabla RetoUsuario, dejando solo el más antiguo."

    def handle(self, *args, **options):
        # Buscar registros duplicados
        duplicados = (
            RetoUsuario.objects.values('usuario', 'reto')
            .annotate(total=Count('id'), min_id=Min('id'))
            .filter(total__gt=1)
        )

        # Eliminar duplicados, manteniendo solo el más antiguo
        eliminados = 0
        for duplicado in duplicados:
            RetoUsuario.objects.filter(
                usuario_id=duplicado['usuario'],
                reto_id=duplicado['reto']
            ).exclude(id=duplicado['min_id']).delete()
            eliminados += duplicado['total'] - 1

        # Mensaje de éxito
        self.stdout.write(
            self.style.SUCCESS(f"{eliminados} registros duplicados eliminados exitosamente.")
        )