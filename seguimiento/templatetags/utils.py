from django import template

register = template.Library()

@register.filter
def generate_range(end, start=1):
    """Genera un rango desde el valor 'start' hasta el valor 'end' (incluido)."""
    return range(start, end + 1)