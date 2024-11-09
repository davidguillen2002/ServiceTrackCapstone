from django.urls import path
from . import views

urlpatterns = [
    path('base_conocimiento/', views.base_conocimiento, name='base_conocimiento'),
    path('guia/<int:guia_id>/', views.guia_detalle, name='guia_detalle'),
    #path('dashboard/', views.dashboard, name='dashboard'),
    path('register_service/<int:service_id>/', views.register_service, name='register_service'),
]