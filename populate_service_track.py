# populate_service_track.py
import django
import os
from datetime import date, timedelta
from random import randint, choice

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ServiceTrack.settings')
django.setup()

from ServiceTrack.models import Rol, Usuario, Equipo, Servicio, Categoria, Guia, ObservacionIncidente, Enlace

# Crear roles
tecnico_rol = Rol.objects.get_or_create(nombre="tecnico")[0]
admin_rol = Rol.objects.get_or_create(nombre="administrador")[0]
cliente_rol = Rol.objects.get_or_create(nombre="cliente")[0]

# Crear usuarios (técnicos y clientes)
tecnicos = []
clientes = []

for i in range(5):
    tecnico = Usuario.objects.get_or_create(
        nombre=f"Tecnico {i+1}",
        username=f"tecnico{i+1}",
        password="hashed_password",
        rol=tecnico_rol,
        cedula=f"111222333{i}",
        correo=f"tecnico{i+1}@tech.com",
        celular=f"09999999{i+1}",
        puntos=randint(50, 200)
    )[0]
    tecnicos.append(tecnico)

for i in range(10):
    cliente = Usuario.objects.get_or_create(
        nombre=f"Cliente {i+1}",
        username=f"cliente{i+1}",
        password="hashed_password",
        rol=cliente_rol,
        cedula=f"12345678{i}0",
        correo=f"cliente{i+1}@gmail.com",
        celular=f"09876543{i+1}",
        puntos=0
    )[0]
    clientes.append(cliente)

# Crear equipos para cada cliente
equipos = []
marcas_modelos = [
    ("HP", "Pavilion 15", "Laptop"),
    ("Dell", "Inspiron 14", "Laptop"),
    ("Lenovo", "ThinkPad X1", "Laptop"),
    ("Apple", "MacBook Air", "Laptop"),
    ("Samsung", "Galaxy Tab S7", "Tablet"),
]

for cliente in clientes:
    marca, modelo, tipo = choice(marcas_modelos)
    equipo = Equipo.objects.get_or_create(
        cliente=cliente,
        marca=marca,
        modelo=modelo,
        anio=randint(2018, 2022),
        tipo_equipo=tipo,
        observaciones="Revisión periódica y mantenimiento preventivo"
    )[0]
    equipos.append(equipo)

# Crear servicios para los equipos
servicios = []
for equipo in equipos:
    tecnico = choice(tecnicos)
    fecha_inicio = date(2023, randint(1, 12), randint(1, 28))
    fecha_fin = fecha_inicio + timedelta(days=randint(1, 7))
    servicio = Servicio.objects.get_or_create(
        equipo=equipo,
        tecnico=tecnico,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        calificacion=randint(1, 5),
        comentario_cliente="Excelente servicio y atención al cliente.",
        costo=round(randint(50, 200) + randint(0, 99) / 100, 2)
    )[0]
    servicios.append(servicio)

# Crear categorías de guías
categorias = ["Mantenimiento", "Reparación", "Instalación", "Actualización", "Diagnóstico"]
categorias_obj = []

for nombre in categorias:
    categoria = Categoria.objects.get_or_create(nombre=nombre)[0]
    categorias_obj.append(categoria)

# Crear guías técnicas
guia_titulos = [
    "Guía de Mantenimiento Preventivo para Laptops",
    "Reparación de Pantalla Rota en HP Pavilion",
    "Instalación de Memoria RAM en Dell Inspiron",
    "Actualización de Sistema Operativo en MacBook",
    "Diagnóstico de Fallas de Hardware en Lenovo ThinkPad"
]

for i, categoria in enumerate(categorias_obj):
    guia = Guia.objects.get_or_create(
        titulo=guia_titulos[i],
        descripcion="Instrucciones detalladas para realizar el procedimiento de manera segura y eficiente.",
        categoria=categoria,
        tipo_servicio="Servicio General",
        equipo_marca=marcas_modelos[i][0],
        equipo_modelo=marcas_modelos[i][1],
        puntuacion=round(randint(3, 5) + randint(0, 99) / 100, 2)
    )[0]

# Crear observaciones o incidentes
observacion_tipos = ["Error", "Observación", "Incidente"]
estados = ["Abierto", "Cerrado", "En progreso"]

for servicio in servicios:
    for i in range(randint(1, 3)):
        tipo_observacion = choice(observacion_tipos)
        estado = choice(estados)
        observacion = ObservacionIncidente.objects.get_or_create(
            autor=choice(tecnicos),
            descripcion=f"Reporte de {tipo_observacion} en el servicio de {servicio.equipo.marca} {servicio.equipo.modelo}.",
            tipo_observacion=tipo_observacion,
            comentarios="Se recomienda revisar los detalles del incidente.",
            estado=estado,
            fecha_reportada=servicio.fecha_inicio,
            fecha_fin=servicio.fecha_fin if estado == "Cerrado" else None
        )[0]

# Crear enlaces
for i, guia in enumerate(Guia.objects.all()):
    Enlace.objects.get_or_create(
        servicio=servicios[i % len(servicios)],
        enlace=f"http://manuales.com/manual_{guia.id}",
        descripcion=f"Enlace a la guía de {guia.titulo} para más detalles."
    )

print("Datos de prueba completos y realistas cargados exitosamente.")