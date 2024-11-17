import django
import os
from datetime import date, timedelta
from random import randint, choice
from django.contrib.auth.hashers import make_password

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ServiceTrack.settings')
django.setup()

from ServiceTrack.models import (
    Rol, Usuario, Equipo, Servicio, Repuesto, Categoria, Guia,
    ObservacionIncidente, Enlace, Medalla, Reto, RegistroPuntos, RetoUsuario
)

# Crear roles
tecnico_rol, _ = Rol.objects.get_or_create(nombre="tecnico")
admin_rol, _ = Rol.objects.get_or_create(nombre="administrador")
cliente_rol, _ = Rol.objects.get_or_create(nombre="cliente")

# Crear un conjunto para las cédulas únicas
cedulas_generadas = set()

# Función para generar una cédula única
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
for i in range(20):  # Crear exactamente 20 técnicos
    tecnico_data = {
        "nombre": f"Técnico {i+1}",
        "password": make_password("Monono123"),
        "rol": tecnico_rol,
        "cedula": generar_cedula_unica(),
        "correo": f"tecnico{i+1}@tech.com",
        "celular": f"09999999{i+1}",
        "puntos": randint(50, 500),
        "servicios_completados": randint(5, 50),
        "calificacion_promedio": round(randint(3, 5) + randint(0, 99) / 100, 2),
    }
    tecnico, created = Usuario.objects.get_or_create(
        username=f"tecnico{i+1}", defaults=tecnico_data
    )
    if created:
        tecnicos.append(tecnico)

# Crear clientes
for i in range(20):  # Crear exactamente 20 clientes
    cliente_data = {
        "nombre": f"Cliente {i+1}",
        "password": make_password("Monono123"),
        "rol": cliente_rol,
        "cedula": generar_cedula_unica(),
        "correo": f"cliente{i+1}@gmail.com",
        "celular": f"09876543{i+1}",
    }
    cliente, created = Usuario.objects.get_or_create(
        username=f"cliente{i+1}", defaults=cliente_data
    )
    if created:
        clientes.append(cliente)

# Crear administrador
admin_data = {
    "nombre": "Administrador",
    "password": make_password("Monono123"),
    "rol": admin_rol,
    "cedula": generar_cedula_unica(),
    "correo": "admin@service.com",
    "celular": "0987654321",
}
admin, created = Usuario.objects.get_or_create(username="admin", defaults=admin_data)

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
    for _ in range(randint(1, 3)):  # Cada cliente puede tener de 1 a 3 equipos
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
    for _ in range(randint(1, 3)):  # Cada equipo puede tener de 1 a 3 servicios
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

        # Agregar repuestos asociados
        for _ in range(randint(1, 5)):  # Cada servicio puede tener de 1 a 5 repuestos
            Repuesto.objects.create(
                nombre=f"Repuesto {_ + 1}",
                descripcion="Descripción de prueba para el repuesto",
                costo=round(randint(10, 200) + randint(0, 99) / 100, 2),
                proveedor=f"Proveedor {_ + 1}",
                cantidad=randint(1, 10),
                servicio=servicio,
            )

# Categorías de guías
categorias = ["Mantenimiento", "Reparación", "Instalación", "Actualización", "Diagnóstico", "Optimización", "Seguridad"]
categorias_obj = [Categoria.objects.get_or_create(nombre=categoria)[0] for categoria in categorias]

# Guías Técnicas
for i, categoria in enumerate(categorias_obj):
    for _ in range(10):  # Muchas guías por categoría
        Guia.objects.get_or_create(
            titulo=f"Guía {categoria.nombre} {_+1}",
            descripcion=f"Guía de {categoria.nombre} para equipos avanzados.",
            categoria=categoria,
            tipo_servicio="Servicio Especializado",
            equipo_marca=choice(marcas_modelos)[0],
            equipo_modelo=choice(marcas_modelos)[1],
            puntuacion=round(randint(3, 5) + randint(0, 99) / 100, 2),
        )

print("Datos generados exitosamente con repuestos.")