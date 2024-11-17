import django
import os
from datetime import date, timedelta
from random import randint, choice
from django.contrib.auth.hashers import make_password

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ServiceTrack.settings')
django.setup()

from ServiceTrack.models import (
    Rol, Usuario, Equipo, Servicio, Repuesto, Categoria, Guia,
    ObservacionIncidente, Enlace, Medalla, Reto, RegistroPuntos, RetoUsuario, HistorialReporte
)

# Crear roles
roles = {"tecnico": None, "administrador": None, "cliente": None}
for rol_name in roles.keys():
    rol, _ = Rol.objects.get_or_create(nombre=rol_name)
    roles[rol_name] = rol

# Crear un conjunto para las cédulas únicas
cedulas_generadas = set()

def generar_cedula_unica():
    while True:
        cedula = f"{randint(100000000, 999999999)}"
        if cedula not in cedulas_generadas:
            cedulas_generadas.add(cedula)
            return cedula

# Crear usuarios (técnicos, clientes y administrador)
tecnicos = []
clientes = []

# Crear técnicos
for i in range(20):
    username = f"tecnico{i+1}"
    tecnico_data = {
        "nombre": f"Técnico {i+1}",
        "password": make_password("Monono123"),
        "rol": roles["tecnico"],
        "cedula": generar_cedula_unica(),
        "correo": f"tecnico{i+1}@tech.com",
        "celular": f"09999999{i+1}",
        "puntos": randint(50, 500),
        "servicios_completados": randint(5, 50),
        "calificacion_promedio": round(randint(3, 5) + randint(0, 99) / 100, 2),
    }
    tecnico, created = Usuario.objects.get_or_create(
        username=username, defaults=tecnico_data
    )
    if created:
        tecnicos.append(tecnico)

# Crear clientes
for i in range(20):
    username = f"cliente{i+1}"
    cliente_data = {
        "nombre": f"Cliente {i+1}",
        "password": make_password("Monono123"),
        "rol": roles["cliente"],
        "cedula": generar_cedula_unica(),
        "correo": f"cliente{i+1}@gmail.com",
        "celular": f"09876543{i+1}",
    }
    cliente, created = Usuario.objects.get_or_create(
        username=username, defaults=cliente_data
    )
    if created:
        clientes.append(cliente)

# Crear administrador
admin_username = "admin"
admin_data = {
    "nombre": "Administrador",
    "password": make_password("Monono123"),
    "rol": roles["administrador"],
    "cedula": generar_cedula_unica(),
    "correo": "admin@service.com",
    "celular": "0987654321",
}
Usuario.objects.get_or_create(username=admin_username, defaults=admin_data)

# Crear equipos para cada cliente
equipos = []
marcas_modelos = [
    ("HP", "Pavilion 15", "Laptop"),
    ("Dell", "Inspiron 14", "Laptop"),
    ("Lenovo", "ThinkPad X1", "Laptop"),
    ("Apple", "MacBook Air", "Laptop"),
    ("Samsung", "Galaxy Tab S7", "Tablet"),
    ("Asus", "ZenBook 14", "Laptop"),
    ("Acer", "Aspire 7", "Laptop"),
]

for cliente in clientes:
    for _ in range(randint(1, 3)):
        marca, modelo, tipo = choice(marcas_modelos)
        equipo, created = Equipo.objects.get_or_create(
            cliente=cliente,
            marca=marca,
            modelo=modelo,
            anio=randint(2015, 2023),
            tipo_equipo=tipo,
            observaciones="Equipo asignado para prueba de carga",
        )
        if created:
            equipos.append(equipo)

# Servicios para los equipos
servicios = []
for equipo in equipos:
    for _ in range(randint(1, 3)):
        tecnico = choice(tecnicos)
        fecha_inicio = date(2023, randint(1, 12), randint(1, 28))
        fecha_fin = fecha_inicio + timedelta(days=randint(1, 7))
        servicio, created = Servicio.objects.get_or_create(
            equipo=equipo,
            tecnico=tecnico,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin if randint(0, 1) else None,
            estado=choice(["pendiente", "en_progreso", "completado"]),
            calificacion=randint(1, 5),
            comentario_cliente="Prueba automatizada para registrar datos.",
            diagnostico_inicial="Revisión inicial automática.",
            costo=round(randint(50, 500) + randint(0, 99) / 100, 2),
        )
        if created:
            servicios.append(servicio)

# Asociar observaciones a servicios
for servicio in servicios:
    for _ in range(randint(1, 2)):
        ObservacionIncidente.objects.create(
            servicio=servicio,
            autor=choice(tecnicos),
            descripcion="Incidente registrado automáticamente.",
            tipo_observacion="Revisión técnica",
            estado=choice(["abierto", "cerrado"]),
            fecha_reportada=date(2023, randint(1, 12), randint(1, 28)),
            fecha_fin=None if randint(0, 1) else date(2023, randint(1, 12), randint(1, 28)),
        )

# Crear categorías y guías
categorias = ["Mantenimiento", "Reparación", "Instalación", "Actualización", "Diagnóstico"]
for categoria in categorias:
    cat, _ = Categoria.objects.get_or_create(nombre=categoria)
    for i in range(5):
        Guia.objects.create(
            titulo=f"Guía {categoria} {i+1}",
            descripcion=f"Guía de prueba para {categoria.lower()}",
            categoria=cat,
            tipo_servicio="Servicio General",
            equipo_marca=choice(marcas_modelos)[0],
            equipo_modelo=choice(marcas_modelos)[1],
            puntuacion=randint(3, 5),
        )

# Crear medallas
medallas = []
for i in range(5):
    medalla, _ = Medalla.objects.get_or_create(
        nombre=f"Medalla {i+1}",
        descripcion="Medalla de ejemplo",
        puntos_necesarios=randint(50, 500),
    )
    medallas.append(medalla)

# Crear retos
for i in range(5):
    Reto.objects.get_or_create(
        nombre=f"Reto {i+1}",
        descripcion="Descripción del reto",
        puntos_otorgados=randint(20, 100),
        requisito=randint(1, 10),
    )

# Asignar medallas a técnicos
for tecnico in tecnicos:
    for medalla in medallas:
        if tecnico.puntos >= medalla.puntos_necesarios:
            tecnico.medallas.add(medalla)
    tecnico.save()

print("Población de datos completada exitosamente.")