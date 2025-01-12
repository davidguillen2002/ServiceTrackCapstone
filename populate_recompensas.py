import os
from django.utils.timezone import now
import django

# Configurar entorno de Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ServiceTrack.settings")
django.setup()

from ServiceTrack.models import Recompensa, Reto, Temporada

# Verificar existencia de temporada activa
temporada_actual = Temporada.objects.filter(activa=True).first()
if not temporada_actual:
    raise ValueError("No hay una temporada activa configurada. Por favor, cree y active una temporada antes de continuar.")

# Definición de recompensas por nivel
recompensas_por_nivel = {
    1: [
        {"tipo": "herramienta", "valor": 50.00, "puntos_necesarios": 100, "descripcion": "Juego de destornilladores básico."},
        {"tipo": "capacitacion", "valor": 0.00, "puntos_necesarios": 120, "descripcion": "Acceso a un curso básico de reparaciones."},
        {"tipo": "reconocimiento", "valor": 0.00, "puntos_necesarios": 80, "descripcion": "Certificado de técnico en entrenamiento."},
    ],
    2: [
        {"tipo": "herramienta", "valor": 100.00, "puntos_necesarios": 200, "descripcion": "Multímetro digital profesional."},
        {"tipo": "capacitacion", "valor": 0.00, "puntos_necesarios": 220, "descripcion": "Curso avanzado de diagnóstico y reparación."},
        {"tipo": "reconocimiento", "valor": 0.00, "puntos_necesarios": 180, "descripcion": "Placa de reconocimiento al mérito técnico."},
    ],
    3: [
        {"tipo": "herramienta", "valor": 200.00, "puntos_necesarios": 300, "descripcion": "Set completo de herramientas de precisión."},
        {"tipo": "bono", "valor": 150.00, "puntos_necesarios": 320, "descripcion": "Bono por desempeño destacado en reparaciones."},
        {"tipo": "capacitacion", "valor": 0.00, "puntos_necesarios": 280, "descripcion": "Curso especializado en tecnología avanzada."},
    ],
    4: [
        {"tipo": "herramienta", "valor": 300.00, "puntos_necesarios": 500, "descripcion": "Equipo avanzado de diagnóstico electrónico."},
        {"tipo": "bono", "valor": 200.00, "puntos_necesarios": 520, "descripcion": "Bono por liderar proyectos técnicos."},
        {"tipo": "reconocimiento", "valor": 0.00, "puntos_necesarios": 480, "descripcion": "Trofeo técnico destacado del año."},
    ],
    5: [
        {"tipo": "herramienta", "valor": 500.00, "puntos_necesarios": 1000, "descripcion": "Estación de soldadura de alta precisión."},
        {"tipo": "bono", "valor": 300.00, "puntos_necesarios": 1020, "descripcion": "Bono especial por maestría técnica."},
        {"tipo": "reconocimiento", "valor": 0.00, "puntos_necesarios": 980, "descripcion": "Inscripción en el salón de la fama técnica."},
    ],
}

# Crear recompensas por nivel basadas en los retos existentes
for nivel, recompensas in recompensas_por_nivel.items():
    # Obtener retos del nivel actual
    retos_nivel = Reto.objects.filter(nivel=nivel, temporada=temporada_actual)
    if not retos_nivel.exists():
        print(f"No se encontraron retos para el nivel {nivel}.")
        continue

    for recompensa_data in recompensas:
        for reto in retos_nivel:
            recompensa, created = Recompensa.objects.get_or_create(
                reto=reto,
                temporada=temporada_actual,
                tipo=recompensa_data["tipo"],
                descripcion=recompensa_data["descripcion"],
                defaults={
                    "valor": recompensa_data["valor"],
                    "puntos_necesarios": recompensa_data["puntos_necesarios"],
                },
            )
            if created:
                print(f"Recompensa creada: {recompensa.descripcion} para el reto '{reto.nombre}' (Nivel {nivel}).")
            else:
                print(f"Recompensa ya existente: {recompensa.descripcion} para el reto '{reto.nombre}' (Nivel {nivel}).")

print("Recompensas creadas exitosamente para la temporada activa.")