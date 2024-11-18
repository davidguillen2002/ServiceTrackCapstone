# servicios/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('base_conocimiento/', views.base_conocimiento, name='base_conocimiento'),
    path('guia/<int:guia_id>/', views.guia_detalle, name='guia_detalle'),
    path('knowledge_dashboard/', views.knowledge_dashboard, name='knowledge_dashboard'),
    path('register_service/<int:service_id>/', views.register_service, name='register_service'),
    path('tecnico_services/', views.tecnico_services_list, name='tecnico_services_list'),
    path("registrar_servicio/", views.registrar_servicio, name="registrar_servicio"),
    path("lista_servicios/", views.lista_servicios, name="lista_servicios"),
    path('<int:servicio_id>/detalle/', views.detalle_servicio, name='detalle_servicio'),
    path("eliminar_servicio/<int:servicio_id>/", views.eliminar_servicio, name="eliminar_servicio"),
    path("actualizar_servicio/<int:servicio_id>/", views.actualizar_servicio, name="actualizar_servicio"),  # Nueva URL para actualizar servicio
    path('equipo/<int:equipo_id>/historial/', views.historial_servicios, name='historial_servicios'),
    path('servicio/<int:servicio_id>/confirmar_entrega/', views.confirmar_entrega, name='confirmar_entrega'),
    path('usuarios/equipo/<int:equipo_id>/actualizar_estado/', views.actualizar_estado_equipo_tecnico,
         name='actualizar_estado_equipo_tecnico'),
    path('mis_servicios_cliente/', views.lista_servicios_cliente, name='lista_servicios_cliente'),
path('enviar_codigo_tecnico/<int:servicio_id>/', views.enviar_codigo_tecnico, name='enviar_codigo_tecnico'),

]