from django import template
import os

register = template.Library()

@register.filter
def startswith(value, arg):
    """Verifica si una cadena comienza con el argumento proporcionado"""
    return str(value).startswith(arg)

@register.filter
def basename(value):
    """
    Extrae solo el nombre del archivo de una ruta.
    """
    return os.path.basename(value)