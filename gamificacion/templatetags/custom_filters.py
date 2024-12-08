from django import template

register = template.Library()

@register.filter
def startswith(value, arg):
    """Verifica si una cadena comienza con el argumento proporcionado"""
    return str(value).startswith(arg)