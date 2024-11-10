# servicios/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Vista de Base de Conocimientos (disponible para técnicos y administradores)
    path('base_conocimiento/', views.base_conocimiento, name='base_conocimiento'),

    # Vista de detalle de guía (disponible para técnicos y administradores)
    path('guia/<int:guia_id>/', views.guia_detalle, name='guia_detalle'),

    # Dashboard de Base de Conocimientos (exclusivo para administradores)
    path('knowledge_dashboard/', views.knowledge_dashboard, name='knowledge_dashboard'),

    # Registro de servicio para obtener guías recomendadas (disponible para técnicos y administradores)
    path('register_service/<int:service_id>/', views.register_service, name='register_service'),
]