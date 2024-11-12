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
    path("eliminar_servicio/<int:servicio_id>/", views.eliminar_servicio, name="eliminar_servicio"),
    path("actualizar_servicio/<int:servicio_id>/", views.actualizar_servicio, name="actualizar_servicio"),  # Nueva URL para actualizar servicio
]