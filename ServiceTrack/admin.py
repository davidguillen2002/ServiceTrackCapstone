# ServiceTrack/admin.py
from django.contrib import admin
from .models import Rol, Usuario, Equipo, Servicio, Categoria, Guia, ObservacionIncidente, Enlace

admin.site.register(Rol)
admin.site.register(Usuario)
admin.site.register(Equipo)
admin.site.register(Servicio)
admin.site.register(Categoria)
admin.site.register(Guia)
admin.site.register(ObservacionIncidente)
admin.site.register(Enlace)