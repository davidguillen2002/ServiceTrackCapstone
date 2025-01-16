from django import template
import re

register = template.Library()

@register.filter
def youtube_id(value):
    """
    Extrae el ID del video de un enlace de YouTube.
    Admite enlaces largos y cortos.
    """
    pattern = r'(?:v=|youtu\.be/|embed/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, value)
    return match.group(1) if match else ''