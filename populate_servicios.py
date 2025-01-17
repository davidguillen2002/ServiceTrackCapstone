import os
import random
from faker import Faker
from datetime import datetime, timedelta
import django

# Configurar entorno de Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ServiceTrack.settings")
django.setup()

from ServiceTrack.models import Servicio, Equipo, Usuario, Temporada, Repuesto, ObservacionIncidente, TipoObservacion

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

# Ponderación de diagnósticos para una selección más realista
diagnosticos_ponderados = [
    (diagnosticos_iniciales[0], 30),  # Ejemplo: encendido, 30% de probabilidad
    (diagnosticos_iniciales[1], 15),
    (diagnosticos_iniciales[2], 20),
    (diagnosticos_iniciales[3], 10),
    (diagnosticos_iniciales[4], 10),
    (diagnosticos_iniciales[5], 5),
    (diagnosticos_iniciales[6], 5),
    (diagnosticos_iniciales[7], 3),
    (diagnosticos_iniciales[8], 1),
    (diagnosticos_iniciales[9], 1),
]

# Repuestos reales basados en diagnósticos
repuestos_por_diagnostico = {
    "Problemas con el encendido del equipo.": ["Fuente de poder", "Placa base"],
    "Pantalla con líneas o defectos de visualización.": ["Pantalla LCD", "Cable flex"],
    "El equipo presenta sobrecalentamiento.": ["Ventilador", "Pasta térmica"],
    "Problemas de conexión Wi-Fi.": ["Tarjeta de red", "Antena Wi-Fi"],
    "Reemplazo de batería necesario.": ["Batería original"],
    "El teclado no responde correctamente.": ["Teclado", "Controlador interno"],
    "Actualización del sistema operativo requerida.": [],
    "El equipo no reconoce dispositivos USB.": ["Puerto USB", "Placa controladora"],
    "Fallos intermitentes en la tarjeta gráfica.": ["Tarjeta gráfica", "Cable interno"],
    "El cargador del equipo está defectuoso.": ["Cargador original"],
}

# Tipos de observaciones
observaciones_posibles = [
    "Retraso en repuestos",
    "Problema no diagnosticado",
    "Cliente no disponible",
    "Herramienta faltante",
    "Revisión pendiente",
]

# Crear tipos de observaciones si no existen
for observacion in observaciones_posibles:
    TipoObservacion.objects.get_or_create(nombre=observacion)

# Fechas de inicio y fin para 2023 y 2024
fecha_inicio_servicio = datetime(2023, 1, 1)
fecha_fin_servicio = datetime(2024, 12, 31)

# Obtener la temporada actual, si existe
temporada_actual = Temporada.obtener_temporada_actual()
if not temporada_actual:
    print("Advertencia: No se encontró una temporada activa. Los servicios creados no estarán asociados a una temporada específica.")

# Variables de progreso
servicios_creados = 0
repuestos_creados = 0
observaciones_creadas = 0
errores = 0

# Crear servicios masivos
for _ in range(5000):  # Crear 5000 servicios
    try:
        tecnico = random.choice(tecnicos)
        cliente = random.choice(clientes)
        equipo = random.choice(equipos)

        # Generar fechas aleatorias dentro del rango
        fecha_inicio = fake.date_between_dates(date_start=fecha_inicio_servicio, date_end=fecha_fin_servicio)
        fecha_fin = fecha_inicio + timedelta(days=random.randint(1, 15)) if random.random() > 0.3 else None
        estado = random.choice(["pendiente", "en_progreso", "completado"])
        calificacion = random.uniform(1, 5) if estado == "completado" else None

        # Seleccionar diagnóstico inicial basado en ponderaciones
        diagnostico = random.choices(
            [d[0] for d in diagnosticos_ponderados],
            weights=[d[1] for d in diagnosticos_ponderados],
            k=1
        )[0]
        repuestos_diagnostico = repuestos_por_diagnostico.get(diagnostico, [])

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
            diagnostico_inicial=diagnostico,
        )
        servicio.save()
        servicios_creados += 1

        # Asignar repuestos al servicio
        for nombre_repuesto in repuestos_diagnostico:
            repuesto = Repuesto(
                nombre=nombre_repuesto,
                descripcion=f"Repuesto para {diagnostico.lower()}",
                costo=round(random.uniform(10.0, 200.0), 2),
                proveedor=fake.company(),
                cantidad=random.randint(1, 3),
                servicio=servicio,
            )
            repuesto.save()
            repuestos_creados += 1

        # Agregar observaciones a servicios no completados
        if estado in ["pendiente", "en_progreso"]:
            tipo_observacion = random.choice(TipoObservacion.objects.all())
            observacion = ObservacionIncidente(
                servicio=servicio,
                autor=tecnico,
                descripcion=fake.paragraph(nb_sentences=3),
                tipo_observacion=tipo_observacion,
                estado="En progreso",
                fecha_reportada=fake.date_between(start_date=fecha_inicio, end_date=fecha_fin or datetime.now()),
            )
            observacion.save()
            observaciones_creadas += 1

    except Exception as e:
        print(f"Error al crear servicio: {e}")
        errores += 1

# Resumen de creación
print(f"Servicios generados exitosamente: {servicios_creados}")
print(f"Repuestos asignados exitosamente: {repuestos_creados}")
print(f"Observaciones creadas exitosamente: {observaciones_creadas}")
if errores > 0:
    print(f"Errores encontrados al crear servicios: {errores}")