# Población de datos completa y ajustada para garantizar funcionalidad y robustez
import django
from django.db import models
from faker import Faker
import os
from datetime import date, timedelta
from random import randint, choice
from django.contrib.auth.hashers import make_password

# Configuración de Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ServiceTrack.settings")
django.setup()

from gamificacion.utils import verificar_y_asignar_medallas_y_retos


# Algoritmo para generar cédulas válidas
def generar_cedula_ecuador():
    provincia = str(randint(1, 24)).zfill(2)
    tercer_digito = str(randint(0, 5))
    secuencial = str(randint(1, 999999)).zfill(6)
    cedula_sin_verificador = provincia + tercer_digito + secuencial

    suma_impar = 0
    for i in range(0, 9, 2):
        multiplicacion = int(cedula_sin_verificador[i]) * 2
        suma_impar += multiplicacion if multiplicacion <= 9 else multiplicacion - 9
    suma_par = sum(map(int, cedula_sin_verificador[1::2]))
    resultado = 10 - ((suma_impar + suma_par) % 10)
    verificador = resultado if resultado < 10 else 0

    return cedula_sin_verificador + str(verificador)

# Configuración de Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ServiceTrack.settings")
django.setup()

from ServiceTrack.models import (
    Rol,
    Usuario,
    Equipo,
    Servicio,
    Categoria,
    Guia,
    Medalla,
    Reto,
    Recompensa,
    RetoUsuario,
    RegistroPuntos,
)

# Crear roles
roles = {"tecnico": None, "administrador": None, "cliente": None}
for rol_name in roles.keys():
    rol, created = Rol.objects.get_or_create(nombre=rol_name)
    roles[rol_name] = rol
    print(f"Rol '{rol_name}' {'creado' if created else 'ya existe'}.")

# Crear administrador
admin_username = "admin"
admin_data = {
    "nombre": "Carla Romero",
    "username": admin_username,
    "password": make_password("Admin12345"),
    "rol": roles["administrador"],
    "cedula": generar_cedula_ecuador(),
    "correo": "admin@reparacionesec.com",
    "celular": "0998765432",
}
Usuario.objects.get_or_create(username=admin_username, defaults=admin_data)

# Crear técnicos
tecnico_nombres = ["Luis Morales", "Ana López", "Carlos Jiménez", "María Pérez"]
tecnicos = []
for nombre in tecnico_nombres:
    username = nombre.lower().replace(" ", "_")
    tecnico_data = {
        "nombre": nombre,
        "username": username,
        "password": make_password("Tecnico123"),
        "rol": roles["tecnico"],
        "cedula": generar_cedula_ecuador(),
        "correo": f"{username}@reparacionesec.com",
        "celular": f"099{randint(1000000, 9999999)}",
        "puntos": 50,  # Puntos iniciales para nivel 1
        "experiencia": 50,  # Experiencia inicial para nivel 1
        "nivel": 1,  # Iniciar en nivel 1
        "servicios_completados": 0,  # Inicialmente sin servicios completados
        "calificacion_promedio": 0.0,  # Sin calificación inicial
    }
    tecnico, created = Usuario.objects.get_or_create(username=username, defaults=tecnico_data)
    if created:
        tecnicos.append(tecnico)

        # Obtener retos para el nivel 1
        retos_nivel_1 = list(Reto.objects.filter(nivel=1)[:3])  # Tomar 3 retos del nivel 1

        # Asignar un reto cumplido, un reto en progreso y un reto en cero
        if len(retos_nivel_1) >= 3:
            # Reto cumplido
            reto_cumplido = retos_nivel_1[0]
            RetoUsuario.objects.create(
                usuario=tecnico,
                reto=reto_cumplido,
                cumplido=True,
                progreso=100,
                cantidad_actual=reto_cumplido.valor_objetivo,
                fecha_completado=date.today(),
            )

            # Asignar la medalla correspondiente al reto cumplido
            medalla_asociada = Medalla.objects.filter(retos_asociados=reto_cumplido).first()
            if medalla_asociada:
                tecnico.medallas.add(medalla_asociada)

            # Reto en progreso
            reto_progreso = retos_nivel_1[1]
            RetoUsuario.objects.create(
                usuario=tecnico,
                reto=reto_progreso,
                cumplido=False,
                progreso=50,  # Progreso inicial al 50%
                cantidad_actual=reto_progreso.valor_objetivo // 2,
            )

            # Reto en cero
            reto_cero = retos_nivel_1[2]
            RetoUsuario.objects.create(
                usuario=tecnico,
                reto=reto_cero,
                cumplido=False,
                progreso=0,
                cantidad_actual=0,
            )

        tecnico.save()

# Crear clientes masivos con nombres reales
fake = Faker("es_ES")  # Generar nombres en español
cliente_nombres = [fake.name() for _ in range(200)]  # Generar 200 nombres reales

clientes = []
for nombre in cliente_nombres:
    username = nombre.lower().replace(" ", "_").replace(".", "")
    cliente_data = {
        "nombre": nombre,
        "username": username,
        "password": make_password("Cliente123"),
        "rol": roles["cliente"],
        "cedula": generar_cedula_ecuador(),
        "correo": f"{username}@gmail.com",
        "celular": f"098{randint(1000000, 9999999)}",
    }
    cliente, created = Usuario.objects.get_or_create(username=username, defaults=cliente_data)
    if created:
        clientes.append(cliente)

# Crear equipos masivos con variedad de marcas reales
equipos = []
marcas_modelos = [
    ("HP", "Pavilion 15", "Laptop"),
    ("Dell", "Inspiron 14", "Laptop"),
    ("Apple", "MacBook Air", "Laptop"),
    ("Samsung", "Galaxy Tab S7", "Tablet"),
    ("Lenovo", "ThinkPad X1", "Laptop"),
    ("Asus", "ZenBook 14", "Laptop"),
    ("Acer", "Swift 3", "Laptop"),
    ("Microsoft", "Surface Pro 7", "Tablet"),
    ("Sony", "Vaio Z", "Laptop"),
    ("Toshiba", "Dynabook", "Laptop"),
]
for cliente in clientes:
    for _ in range(randint(1, 5)):  # Cada cliente tiene de 1 a 5 equipos
        marca, modelo, tipo = choice(marcas_modelos)
        equipo_data = {
            "cliente": cliente,
            "marca": marca,
            "modelo": modelo,
            "anio": randint(2015, 2023),
            "tipo_equipo": tipo,
            "observaciones": fake.text(max_nb_chars=50),  # Observaciones generadas de manera realista
        }
        equipo, created = Equipo.objects.get_or_create(**equipo_data)
        if created:
            equipos.append(equipo)

# Crear servicios masivos con datos realistas
comentarios_cliente = [
    "Excelente servicio, muy rápido y eficiente.",
    "El técnico fue amable y resolvió el problema.",
    "Quedé satisfecho con el servicio prestado.",
    "Hubo algunos problemas, pero se resolvieron.",
    "Buen trabajo, aunque podría mejorar en tiempos.",
    "El servicio fue adecuado, aunque tardó un poco más de lo esperado.",
    "El técnico explicó todo muy bien.",
    "No quedé satisfecho con el tiempo de entrega.",
    "El trabajo fue bueno, pero esperaba más.",
    "Servicio excelente, superó mis expectativas.",
]

diagnosticos_iniciales = [
    "El equipo no enciende correctamente.",
    "Pantalla dañada y necesita reemplazo.",
    "Problemas con el sistema operativo.",
    "La batería no dura más de 2 horas.",
    "El equipo presenta sobrecalentamiento.",
    "El equipo emite ruidos extraños al encender.",
    "Teclado con algunas teclas inservibles.",
    "Problema con la conexión Wi-Fi.",
    "El equipo se reinicia inesperadamente.",
    "Problemas con el cargador del equipo.",
]

# Crear servicios masivos con datos realistas y balanceados
for tecnico in tecnicos:
    # Cada técnico tendrá un servicio completado y el resto en estados diferentes
    servicios_creados = []

    # Crear un servicio completado
    equipo = choice(equipos)
    fecha_inicio = date.today() - timedelta(days=randint(30, 365))  # Servicio en el último año
    fecha_fin = fecha_inicio + timedelta(days=randint(1, 15))  # Servicio dura entre 1 y 15 días
    calificacion = 3  # Calificación fija en 3

    servicio_completado = Servicio(
        equipo=equipo,
        tecnico=tecnico,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        estado="completado",
        calificacion=calificacion,
        costo=round(randint(50, 500) + randint(0, 99) / 100, 2),
        comentario_cliente="Servicio inicial completado con éxito.",
        diagnostico_inicial="Diagnóstico inicial adecuado para nivel básico.",
    )
    servicios_creados.append(servicio_completado)

    # Crear servicios en otros estados
    estados_restantes = ["pendiente", "en_progreso"]
    for _ in range(4):  # Crear 4 servicios adicionales con diferentes estados
        estado = choice(estados_restantes)
        servicio = Servicio(
            equipo=choice(equipos),
            tecnico=tecnico,
            fecha_inicio=date.today() - timedelta(days=randint(15, 90)),
            fecha_fin=None if estado != "completado" else date.today() - timedelta(days=randint(1, 7)),
            estado=estado,
            calificacion=None if estado != "completado" else 3,  # Calificación fija en 3
            costo=round(randint(50, 500) + randint(0, 99) / 100, 2),
            comentario_cliente=None if estado != "completado" else "Buen servicio.",
            diagnostico_inicial="Diagnóstico en progreso." if estado != "completado" else "Diagnóstico finalizado.",
        )
        servicios_creados.append(servicio)

    # Guardar todos los servicios en un solo paso para optimizar rendimiento
    Servicio.objects.bulk_create(servicios_creados)

    # Registrar puntos únicamente para el servicio completado
    puntos_servicio = 10 + max(0, (servicio_completado.calificacion or 0) - 2) * 5
    if tecnico.puntos + puntos_servicio > 100:  # Limitar al nivel 1
        puntos_servicio = 100 - tecnico.puntos

    RegistroPuntos.objects.create(
        usuario=tecnico,
        servicio=servicio_completado,
        puntos_obtenidos=puntos_servicio,
        descripcion=f"Servicio {servicio_completado.id} completado",
    )

    # Actualizar estadísticas del técnico
    tecnico.servicios_completados = 1  # Solo un servicio completado
    tecnico.puntos += puntos_servicio
    tecnico.experiencia = min(tecnico.experiencia + 10, 100)  # Limitar experiencia para nivel 1
    tecnico.save()

print("Servicios generados y progreso actualizado exitosamente.")

# Crear categorías y guías
categorias = ["Mantenimiento", "Reparación", "Diagnóstico"]
for categoria in categorias:
    cat, _ = Categoria.objects.get_or_create(nombre=categoria)
    for i in range(3):
        Guia.objects.create(
            titulo=f"Guía {categoria} {i + 1}",
            descripcion=f"Guía detallada sobre {categoria.lower()}.",
            categoria=cat,
        )

# Crear medallas y retos dinámicos automáticamente
medallas_por_nivel = {
    1: [
        {
            "nombre": "Iniciado en Reparaciones",
            "descripcion": "Completa 5 servicios exitosos.",
            "puntos_necesarios": 50,
            "nivel_requerido": 1,
            "icono": "medallas/nivel 1-1.png",
            "retos": [
                {
                    "nombre": "Primer Servicio",
                    "descripcion": "Completa tu primer servicio exitosamente.",
                    "criterio": "servicios",
                    "valor_objetivo": 1,
                    "puntos_otorgados": 50,
                }
            ],
        },
        {
            "nombre": "Primer Técnico",
            "descripcion": "Acumula 100 puntos.",
            "puntos_necesarios": 100,
            "nivel_requerido": 1,
            "icono": "medallas/nivel 1-2.png",
            "retos": [
                {
                    "nombre": "Acumula Puntos Básicos",
                    "descripcion": "Acumula al menos 100 puntos.",
                    "criterio": "puntos",
                    "valor_objetivo": 100,
                    "puntos_otorgados": 30,
                }
            ],
        },
        {
            "nombre": "Calificación Promedio Inicial",
            "descripcion": "Obtén una calificación promedio mínima de 3.",
            "puntos_necesarios": 0,
            "nivel_requerido": 1,
            "icono": "medallas/nivel 1-3.png",
            "retos": [
                {
                    "nombre": "Calificación Inicial",
                    "descripcion": "Obtén una calificación promedio mínima de 3.",
                    "criterio": "calificaciones",
                    "valor_objetivo": 3,
                    "puntos_otorgados": 40,
                }
            ],
        },
    ],
    2: [
        {
            "nombre": "Técnico en Ascenso",
            "descripcion": "Completa 10 servicios exitosos.",
            "puntos_necesarios": 200,
            "nivel_requerido": 2,
            "icono": "medallas/nivel 2-1.png",
            "retos": [
                {
                    "nombre": "Servicio Rápido",
                    "descripcion": "Completa 10 servicios en menos de 7 días.",
                    "criterio": "servicios",
                    "valor_objetivo": 10,
                    "puntos_otorgados": 70,
                }
            ],
        },
        {
            "nombre": "Puntos Intermedios",
            "descripcion": "Acumula 200 puntos.",
            "puntos_necesarios": 200,
            "nivel_requerido": 2,
            "icono": "medallas/nivel 2-2.png",
            "retos": [
                {
                    "nombre": "Puntos Progresivos",
                    "descripcion": "Acumula 200 puntos.",
                    "criterio": "puntos",
                    "valor_objetivo": 200,
                    "puntos_otorgados": 50,
                }
            ],
        },
        {
            "nombre": "Calificación Intermedia",
            "descripcion": "Obtén una calificación promedio mínima de 4.",
            "puntos_necesarios": 0,
            "nivel_requerido": 2,
            "icono": "medallas/nivel 2-3.png",
            "retos": [
                {
                    "nombre": "Calificación Excelente",
                    "descripcion": "Obtén una calificación promedio de al menos 4.",
                    "criterio": "calificaciones",
                    "valor_objetivo": 4,
                    "puntos_otorgados": 60,
                }
            ],
        },
    ],
    3: [
        {
            "nombre": "Experto en Reparaciones",
            "descripcion": "Completa 20 servicios exitosos.",
            "puntos_necesarios": 300,
            "nivel_requerido": 3,
            "icono": "medallas/nivel 3-1.png",
            "retos": [
                {
                    "nombre": "Avance Profesional",
                    "descripcion": "Completa 20 servicios exitosos.",
                    "criterio": "servicios",
                    "valor_objetivo": 20,
                    "puntos_otorgados": 100,
                }
            ],
        },
        {
            "nombre": "Puntos Avanzados",
            "descripcion": "Acumula 500 puntos.",
            "puntos_necesarios": 500,
            "nivel_requerido": 3,
            "icono": "medallas/nivel 3-2.png",
            "retos": [
                {
                    "nombre": "Puntos Avanzados",
                    "descripcion": "Acumula 500 puntos.",
                    "criterio": "puntos",
                    "valor_objetivo": 500,
                    "puntos_otorgados": 90,
                }
            ],
        },
        {
            "nombre": "Calificación Sobresaliente",
            "descripcion": "Obtén una calificación promedio mínima de 4.5.",
            "puntos_necesarios": 0,
            "nivel_requerido": 3,
            "icono": "medallas/nivel 3-3.png",
            "retos": [
                {
                    "nombre": "Calificación Sobresaliente",
                    "descripcion": "Obtén una calificación promedio de al menos 4.5.",
                    "criterio": "calificaciones",
                    "valor_objetivo": 4.5,
                    "puntos_otorgados": 80,
                }
            ],
        },
    ],
    4: [
        {
            "nombre": "Técnico Avanzado",
            "descripcion": "Completa 30 servicios exitosos.",
            "puntos_necesarios": 700,
            "nivel_requerido": 4,
            "icono": "medallas/nivel 4-1.png",
            "retos": [
                {
                    "nombre": "Técnico Experto",
                    "descripcion": "Completa 30 servicios exitosos.",
                    "criterio": "servicios",
                    "valor_objetivo": 30,
                    "puntos_otorgados": 150,
                }
            ],
        },
        {
            "nombre": "Puntos Máximos",
            "descripcion": "Acumula 1000 puntos.",
            "puntos_necesarios": 1000,
            "nivel_requerido": 4,
            "icono": "medallas/nivel 4-2.png",
            "retos": [
                {
                    "nombre": "Puntos Máximos",
                    "descripcion": "Acumula 1000 puntos.",
                    "criterio": "puntos",
                    "valor_objetivo": 1000,
                    "puntos_otorgados": 120,
                }
            ],
        },
        {
            "nombre": "Calificación Perfecta",
            "descripcion": "Obtén una calificación promedio de 5.",
            "puntos_necesarios": 0,
            "nivel_requerido": 4,
            "icono": "medallas/nivel 4-3.png",
            "retos": [
                {
                    "nombre": "Calificación Perfecta",
                    "descripcion": "Obtén una calificación promedio de 5.",
                    "criterio": "calificaciones",
                    "valor_objetivo": 5,
                    "puntos_otorgados": 140,
                }
            ],
        },
    ],
    5: [
        {
            "nombre": "Maestro Técnico",
            "descripcion": "Completa 50 servicios exitosos.",
            "puntos_necesarios": 1500,
            "nivel_requerido": 5,
            "icono": "medallas/nivel 5-1.png",
            "retos": [
                {
                    "nombre": "Maestro Técnico",
                    "descripcion": "Completa 50 servicios exitosos.",
                    "criterio": "servicios",
                    "valor_objetivo": 50,
                    "puntos_otorgados": 200,
                }
            ],
        },
        {
            "nombre": "Dominio Total",
            "descripcion": "Acumula 2000 puntos.",
            "puntos_necesarios": 2000,
            "nivel_requerido": 5,
            "icono": "medallas/nivel 5-2.png",
            "retos": [
                {
                    "nombre": "Dominio Total",
                    "descripcion": "Acumula 2000 puntos.",
                    "criterio": "puntos",
                    "valor_objetivo": 2000,
                    "puntos_otorgados": 250,
                }
            ],
        },
        {
            "nombre": "Excelencia Continua",
            "descripcion": "Mantén una calificación promedio de 4.8 o más en los últimos 10 servicios.",
            "puntos_necesarios": 0,
            "nivel_requerido": 5,
            "icono": "medallas/nivel 5-3.png",
            "retos": [
                {
                    "nombre": "Excelencia Continua",
                    "descripcion": "Mantén una calificación promedio de 4.8 o más en los últimos 10 servicios.",
                    "criterio": "calificaciones",
                    "valor_objetivo": 4.8,
                    "puntos_otorgados": 300,
                }
            ],
        },
    ],
}

# Crear y asignar medallas y retos automáticamente
for nivel, medallas in medallas_por_nivel.items():
    for medalla_data in medallas:
        retos_data = medalla_data["retos"]  # No eliminar el campo del diccionario
        medalla, created = Medalla.objects.get_or_create(
            nombre=medalla_data["nombre"],
            descripcion=medalla_data["descripcion"],
            puntos_necesarios=medalla_data["puntos_necesarios"],
            nivel_requerido=medalla_data["nivel_requerido"],
            icono=medalla_data["icono"],
        )
        if created:
            print(f"Medalla '{medalla.nombre}' creada para nivel {nivel}.")

        # Crear y asociar retos a la medalla
        for reto_data in retos_data:
            reto, _ = Reto.objects.get_or_create(
                nombre=reto_data["nombre"],
                descripcion=reto_data["descripcion"],
                puntos_otorgados=reto_data["puntos_otorgados"],
                criterio=reto_data["criterio"],
                valor_objetivo=reto_data["valor_objetivo"],
                nivel=nivel,
            )
            medalla.retos_asociados.add(reto)
        medalla.save()

print("Medallas y retos creados correctamente.")

# Crear recompensas específicas por nivel para técnicos
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

# Crear y asignar recompensas automáticamente según retos cumplidos
for nivel, recompensas in recompensas_por_nivel.items():
    for recompensa_data in recompensas:
        for tecnico in tecnicos:
            # Verificar retos asociados al nivel del técnico
            retos_cumplidos = RetoUsuario.objects.filter(usuario=tecnico, reto__nivel=nivel, cumplido=True).count()
            retos_requeridos = Reto.objects.filter(nivel=nivel).count()

            if retos_cumplidos == retos_requeridos:  # Todos los retos del nivel están cumplidos
                recompensa, created = Recompensa.objects.get_or_create(
                    usuario=tecnico,
                    tipo=recompensa_data["tipo"],
                    puntos_necesarios=recompensa_data["puntos_necesarios"],
                    descripcion=recompensa_data["descripcion"],
                    defaults={
                        "valor": recompensa_data["valor"],
                        "redimido": False,
                    }
                )
                if created:
                    print(f"[Nivel {nivel}] Recompensa '{recompensa.descripcion}' asignada a técnico '{tecnico.nombre}'.")
                else:
                    print(f"[Nivel {nivel}] Recompensa '{recompensa.descripcion}' ya existe para técnico '{tecnico.nombre}'.")
            else:
                print(f"Técnico '{tecnico.nombre}' aún no ha cumplido todos los retos de nivel {nivel}.")

# Evaluar progreso y cumplimiento de retos para todos los técnicos
for tecnico in tecnicos:
    print(f"Evaluando retos y medallas para el técnico: {tecnico.nombre}")

    # Llamar a la función centralizada para verificar medallas y retos
    animaciones = verificar_y_asignar_medallas_y_retos(tecnico)

    # Ajustar estadísticas del técnico
    tecnico.calificacion_promedio = (
        Servicio.objects.filter(tecnico=tecnico, estado="completado")
        .aggregate(avg_calificacion=models.Avg("calificacion"))["avg_calificacion"]
        or 0
    )
    tecnico.save()

    # Asegurar que el nivel máximo no sea excedido
    if tecnico.nivel > 5:
        tecnico.nivel = 5
        tecnico.save()
        print(f"Técnico '{tecnico.nombre}' ha sido ajustado al nivel máximo permitido (5).")

# Resumen de progreso y asignaciones
for tecnico in tecnicos:
    print(f"Técnico '{tecnico.nombre}' tiene:")
    print(f"- Nivel: {tecnico.nivel}")
    print(f"- Experiencia: {tecnico.experiencia}")
    print(f"- Puntos: {tecnico.puntos}")
    print(f"- Retos cumplidos: {RetoUsuario.objects.filter(usuario=tecnico, cumplido=True).count()}")
    print(f"- Medallas asignadas: {tecnico.medallas.count()}")

# Resumen de la población de datos
print(f"Técnicos creados: {Usuario.objects.filter(rol=roles['tecnico']).count()}")
print(f"Clientes creados: {Usuario.objects.filter(rol=roles['cliente']).count()}")
print(f"Servicios creados: {Servicio.objects.count()}")

for nivel in range(1, 6):
    total_retos_nivel = sum(len(medalla["retos"]) for medalla in medallas_por_nivel.get(nivel, []))
    retos_cumplidos_nivel = RetoUsuario.objects.filter(reto__nivel=nivel, cumplido=True).count()
    print(f"Nivel {nivel}: Retos cumplidos {retos_cumplidos_nivel}/{total_retos_nivel}")
    print(f"Técnicos en nivel {nivel}: {Usuario.objects.filter(nivel=nivel, rol=roles['tecnico']).count()}")

print(f"Medallas asignadas: {sum(tecnico.medallas.count() for tecnico in tecnicos)}")
print(f"Puntos registrados: {RegistroPuntos.objects.count()}")
print("Población de datos completada exitosamente.")