# Crear servicios masivos para los años 2023 y 2024 con datos detallados
import os
import random
from faker import Faker
from datetime import datetime, timedelta
import django

# Configurar entorno de Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ServiceTrack.settings")
django.setup()

from ServiceTrack.models import Servicio, Equipo, Usuario, Temporada

fake = Faker("es_ES")  # Generador en español

# Verificar que hay datos suficientes antes de proceder
tecnicos = Usuario.objects.filter(rol__nombre="tecnico")
clientes = Usuario.objects.filter(rol__nombre="cliente")
equipos = Equipo.objects.all()

if not tecnicos.exists() or not clientes.exists() or not equipos.exists():
    print("Error: Faltan técnicos, clientes o equipos en la base de datos. Asegúrate de que los datos necesarios estén poblados antes de ejecutar este script.")
    exit()

# Comentarios y diagnósticos posibles
comentarios_cliente = [
    "El servicio fue excelente y rápido.",
    "El técnico explicó todos los pasos.",
    "Estoy satisfecho con el resultado.",
    "El trabajo fue bueno, pero tardó más de lo esperado.",
    "Hubo problemas iniciales, pero el técnico los resolvió.",
    "Recomendaré este servicio a mis amigos.",
    "El técnico fue muy profesional.",
    "El servicio no cumplió mis expectativas.",
    "El equipo quedó como nuevo, ¡excelente trabajo!",
    "El diagnóstico fue preciso y rápido.",
]

diagnosticos_iniciales = [
    "Problemas con el encendido del equipo.",
    "Pantalla con líneas o defectos de visualización.",
    "El equipo presenta sobrecalentamiento.",
    "Problemas de conexión Wi-Fi.",
    "Reemplazo de batería necesario.",
    "El teclado no responde correctamente.",
    "Actualización del sistema operativo requerida.",
    "El equipo no reconoce dispositivos USB.",
    "Fallos intermitentes en la tarjeta gráfica.",
    "El cargador del equipo está defectuoso.",
]

# Fechas de inicio y fin para 2023 y 2024
fecha_inicio_servicio = datetime(2023, 1, 1)
fecha_fin_servicio = datetime(2024, 12, 31)

# Obtener la temporada actual, si existe
temporada_actual = Temporada.obtener_temporada_actual()
if not temporada_actual:
    print("Advertencia: No se encontró una temporada activa. Los servicios creados no estarán asociados a una temporada específica.")

# Crear servicios detallados
servicios_creados = 0
errores = 0

for _ in range(5000):  # Crear 5000 servicios
    try:
        tecnico = random.choice(tecnicos)
        cliente = random.choice(clientes)
        equipo = random.choice(equipos)

        # Generar fechas aleatorias dentro del rango
        fecha_inicio = fake.date_between_dates(date_start=fecha_inicio_servicio, date_end=fecha_fin_servicio)
        fecha_fin = fecha_inicio + timedelta(days=random.randint(1, 15)) if random.random() > 0.2 else None
        estado = random.choice(["pendiente", "en_progreso", "completado"])
        calificacion = random.uniform(1, 5) if estado == "completado" else None

        # Crear servicio
        servicio = Servicio(
            equipo=equipo,
            tecnico=tecnico,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            estado=estado,
            calificacion=round(calificacion, 2) if calificacion else None,
            costo=round(random.uniform(50.00, 500.00), 2),
            comentario_cliente=random.choice(comentarios_cliente) if estado == "completado" else None,
            diagnostico_inicial=random.choice(diagnosticos_iniciales),
        )
        servicio.save()
        servicios_creados += 1
    except Exception as e:
        print(f"Error al crear servicio: {e}")
        errores += 1

print(f"Servicios generados exitosamente: {servicios_creados}")
if errores > 0:
    print(f"Errores encontrados al crear servicios: {errores}")