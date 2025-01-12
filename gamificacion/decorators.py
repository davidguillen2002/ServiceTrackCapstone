from django.shortcuts import redirect
from django.contrib import messages
from ServiceTrack.models import Temporada

def validar_temporada_activa(view_func):
    """
    Decorador para asegurar que solo se procesen vistas cuando haya una temporada activa.
    """
    def wrapper(request, *args, **kwargs):
        temporada_actual = Temporada.obtener_temporada_actual()
        if not temporada_actual:
            messages.error(request, "No hay una temporada activa.")
            return redirect("home")
        return view_func(request, *args, **kwargs)
    return wrapper