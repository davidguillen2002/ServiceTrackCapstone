# notificaciones/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_notificaciones, name='lista_notificaciones'),
    path('<int:notificacion_id>/', views.detalle_notificacion, name='detalle_notificacion'),
    path('marcar_todas/', views.marcar_todas_como_leidas, name='marcar_todas_como_leidas'),
    path('limpiar/', views.limpiar_notificaciones, name='limpiar_notificaciones'),  # Nueva ruta
]