import os
import django

# Configurar entorno de Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ServiceTrack.settings")
django.setup()

from ServiceTrack.models import Servicio

# Obtener los servicios completados sin código de entrega
servicios_completados = Servicio.objects.filter(estado="completado", codigo_entrega__isnull=True)

# Contador para seguimiento
servicios_actualizados = 0

for servicio in servicios_completados:
    try:
        servicio.generar_codigo_entrega()
        servicios_actualizados += 1
        print(f"Código de entrega generado para Servicio {servicio.id}: {servicio.codigo_entrega}")
    except Exception as e:
        print(f"Error al generar código para Servicio {servicio.id}: {e}")

print(f"\nTotal de servicios actualizados con códigos de entrega: {servicios_actualizados}")