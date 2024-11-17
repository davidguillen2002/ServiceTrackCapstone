from django.urls import path
from . import views

urlpatterns = [
    # Vistas para clientes
    path('cliente/panel/', views.panel_cliente, name='panel_cliente'),  # Agregar esta línea
    path('cliente/equipos/', views.lista_equipos_cliente, name='lista_equipos_cliente'),
    path('cliente/equipo/<int:equipo_id>/', views.detalle_equipo_cliente, name='detalle_equipo_cliente'),
    path('servicio/<int:servicio_id>/dejar_resena/', views.dejar_resena, name='dejar_resena'),

    # Vistas para técnicos
    path('usuarios/equipos/', views.lista_equipos_tecnico, name='lista_equipos_tecnico'),
    path('usuarios/equipo/<int:equipo_id>/actualizar_estado/', views.actualizar_estado_equipo_tecnico, name='actualizar_estado_equipo_tecnico'),
    path('usuarios/servicio/<int:servicio_id>/', views.detalle_servicio_tecnico, name='detalle_servicio_tecnico'),
]