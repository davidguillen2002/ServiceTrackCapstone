from django.urls import path
from .views import (
    usuario_list_view,  # Cambiar la lista de usuarios a una FBV
    UsuarioCreateView,
    UsuarioUpdateView,
    UsuarioDeleteView,
    dashboard_view,
    tecnico_dashboard_view,
    cliente_dashboard_view,
)

urlpatterns = [
    path('', dashboard_view, name='dashboard'),  # Ruta principal del dashboard
    path('tecnico/', tecnico_dashboard_view, name='tecnico_dashboard'),
    path('cliente/', cliente_dashboard_view, name='cliente_dashboard'),
    path('usuarios/', usuario_list_view, name='usuario-list'),  # Cambiado a FBV
    path('usuarios/nuevo/', UsuarioCreateView.as_view(), name='usuario-create'),  # Formulario para agregar usuario
    path('usuarios/editar/<int:pk>/', UsuarioUpdateView.as_view(), name='usuario-update'),  # Actualizar usuario
    path('usuarios/eliminar/<int:pk>/', UsuarioDeleteView.as_view(), name='usuario-delete'),  # Eliminar usuario
]