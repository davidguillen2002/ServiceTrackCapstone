from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ServiceTrack.models import Notificacion

@login_required
def lista_notificaciones(request):
    """
    Muestra la lista de notificaciones solo del usuario actual.
    """
    notificaciones = Notificacion.objects.filter(usuario=request.user).order_by('-fecha_creacion')
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
    messages.success(request, "Todas tus notificaciones han sido marcadas como leídas.")
    return redirect('lista_notificaciones')

@login_required
def limpiar_notificaciones(request):
    """
    Elimina todas las notificaciones del usuario actual y redirige a la lista.
    """
    try:
        # Eliminar todas las notificaciones asociadas al usuario actual
        Notificacion.objects.filter(usuario=request.user).delete()
        messages.success(request, "Todas tus notificaciones han sido eliminadas exitosamente.")
    except Exception as e:
        messages.error(request, f"Error al intentar eliminar las notificaciones: {str(e)}")

    return redirect('lista_notificaciones')
