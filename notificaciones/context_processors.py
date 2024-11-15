# notificaciones/context_processors.py
from ServiceTrack.models import Notificacion

def notificaciones_no_leidas(request):
    if request.user.is_authenticated:
        no_leidas = Notificacion.objects.filter(usuario=request.user, leido=False).count()
        return {'notificaciones_no_leidas': no_leidas}
    return {}