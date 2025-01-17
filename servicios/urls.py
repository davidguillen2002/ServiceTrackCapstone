from django.urls import path
from . import views

urlpatterns = [
    path('base_conocimiento/', views.base_conocimiento, name='base_conocimiento'),
    path('guia/<int:guia_id>/', views.guia_detalle, name='guia_detalle'),
    path('knowledge_dashboard/', views.knowledge_dashboard, name='knowledge_dashboard'),
    path('register_service/<int:service_id>/', views.register_service, name='register_service'),
    path('tecnico_services/', views.tecnico_services_list, name='tecnico_services_list'),
    path('registrar_servicio/', views.registrar_servicio, name='registrar_servicio'),
    path('lista_servicios/', views.lista_servicios, name='lista_servicios'),
    path('<int:servicio_id>/detalle/', views.detalle_servicio, name='detalle_servicio'),
    path('eliminar_servicio/<int:servicio_id>/', views.eliminar_servicio, name='eliminar_servicio'),
    path('actualizar_servicio/<int:servicio_id>/', views.actualizar_servicio, name='actualizar_servicio'),
    path('equipo/<int:equipo_id>/historial/', views.historial_servicios, name='historial_servicios'),
    path('servicio/<int:servicio_id>/confirmar_entrega/', views.confirmar_entrega, name='confirmar_entrega'),
    path('usuarios/equipo/<int:equipo_id>/actualizar_estado/', views.actualizar_estado_equipo_tecnico,
         name='actualizar_estado_equipo_tecnico'),
    path('mis_servicios_cliente/', views.lista_servicios_cliente, name='lista_servicios_cliente'),
    path('enviar_codigo_tecnico/<int:servicio_id>/', views.enviar_codigo_tecnico, name='enviar_codigo_tecnico'),
    path('chat/', views.chat, name='chat'),

    # Lista de capacitaciones (técnicos y administradores)
    path('capacitaciones/', views.capacitacion_index, name='capacitacion_index'),

    # CRUD de capacitaciones (solo administradores)
    path('capacitaciones/crear/', views.capacitacion_create, name='capacitacion_create'),
    path('capacitaciones/<int:capacitacion_id>/editar/', views.capacitacion_edit, name='capacitacion_edit'),
    path('capacitaciones/<int:capacitacion_id>/eliminar/', views.capacitacion_delete, name='capacitacion_delete'),

    # Nueva ruta para previsualización de guías
    path('api/guide_preview/<int:guide_id>/', views.guide_preview, name='guide_preview'),

    # Rutas para creación de clientes y servicios (técnicos)
    path('clientes/', views.listar_clientes_tecnico, name='listar_clientes_tecnico'),
    path('clientes/crear/', views.crear_cliente, name='crear_cliente'),
    path('clientes/<int:cliente_id>/detalle/', views.detalle_cliente, name='detalle_cliente'),
    path('servicios/crear/', views.crear_servicio, name='crear_servicio'),

    # Rutas para incidentes
    path('servicio/<int:servicio_id>/incidentes/', views.listar_incidentes, name='listar_incidentes'),
    path('servicio/<int:servicio_id>/incidente/crear/', views.crear_incidente, name='crear_incidente'),

    path('ajax/obtener-cliente/', views.obtener_cliente_por_equipo, name='obtener_cliente_por_equipo'),
    path('servicio/<int:servicio_id>/actualizar_estado/', views.actualizar_estado_servicio, name='actualizar_estado_servicio'),
    path('incidente/<int:incidente_id>/notificar/', views.notificar_incidente, name='notificar_incidente'),
    path('servicio/<int:servicio_id>/agregar_repuesto/', views.agregar_repuesto, name='agregar_repuesto'),
    path('api/equipo_cliente/', views.api_equipo_cliente, name='api_equipo_cliente'),

]