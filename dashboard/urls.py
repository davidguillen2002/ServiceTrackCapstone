# dashboard/urls.py
from django.urls import path
from .views import UsuarioListView, UsuarioCreateView, UsuarioUpdateView, UsuarioDeleteView, dashboard_view

urlpatterns = [
    path('', dashboard_view, name='dashboard'),  # Ruta principal del dashboard
    path('usuarios/', UsuarioListView.as_view(), name='usuario-list'),  # Lista de usuarios
    path('usuarios/nuevo/', UsuarioCreateView.as_view(), name='usuario-create'),  # Formulario para agregar usuario
    path('usuarios/editar/<int:pk>/', UsuarioUpdateView.as_view(), name='usuario-update'),  # Actualizar usuario
    path('usuarios/eliminar/<int:pk>/', UsuarioDeleteView.as_view(), name='usuario-delete'),  # Eliminar usuario
]