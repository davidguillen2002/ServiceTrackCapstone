# seguimiento/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def replace_spaces(value, arg="_"):
    """Reemplaza espacios en el texto por un guion bajo u otro caracter dado"""
    return value.replace(" ", arg)