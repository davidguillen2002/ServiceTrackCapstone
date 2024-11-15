# notificaciones/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from ServiceTrack.models import Notificacion

@login_required
def lista_notificaciones(request):
    """
    Muestra la lista de notificaciones para el usuario actual, filtradas por rol.
    """
    notificaciones = Notificacion.obtener_notificaciones_por_rol(request.user)
    return render(request, 'notificaciones/lista_notificaciones.html', {'notificaciones': notificaciones})

@login_required
def detalle_notificacion(request, notificacion_id):
    """
    Muestra el detalle de una notificación específica y la marca como leída.
    """
    notificacion = get_object_or_404(Notificacion, id=notificacion_id, usuario=request.user)
    if not notificacion.leido:
        notificacion.leido = True
        notificacion.save()
    return render(request, 'notificaciones/detalle_notificacion.html', {'notificacion': notificacion})

@login_required
def marcar_todas_como_leidas(request):
    """
    Marca todas las notificaciones no leídas como leídas para el usuario actual.
    """
    Notificacion.objects.filter(usuario=request.user, leido=False).update(leido=True)
    return redirect('lista_notificaciones')
