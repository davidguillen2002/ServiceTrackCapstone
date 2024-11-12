# populate_retousuario.py
import django
import os
from random import choice, randint
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ServiceTrack.settings')
django.setup()

from ServiceTrack.models import Usuario, Reto, RetoUsuario, Rol

# Seleccionamos el rol de técnico para asignar retos solo a usuarios técnicos
tecnico_rol = Rol.objects.get(nombre="tecnico")
tecnicos = Usuario.objects.filter(rol=tecnico_rol)
retos = Reto.objects.all()

# Poblar la tabla RetoUsuario
for tecnico in tecnicos:
    # Asignamos entre 1 y 3 retos a cada técnico para simular que tienen retos activos
    num_retos = randint(1, 3)
    assigned_retos = []

    for _ in range(num_retos):
        reto = choice(retos)

        # Asegurarse de no asignar el mismo reto dos veces al mismo técnico
        if reto in assigned_retos:
            continue
        assigned_retos.append(reto)

        # Crear una entrada en RetoUsuario
        RetoUsuario.objects.get_or_create(
            usuario=tecnico,
            reto=reto,
            cumplido=bool(randint(0, 1)),  # Marcamos algunos como completados y otros como no
            fecha_completado=(datetime.now() - timedelta(days=randint(0, 30))) if randint(0, 1) else None
        )

print("Tabla RetoUsuario poblada con datos válidos.")