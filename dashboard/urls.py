from django.urls import path
from .views import TecnicoListView, TecnicoCreateView, TecnicoUpdateView, TecnicoDeleteView, dashboard_view

urlpatterns = [
    path('', dashboard_view, name='dashboard'),  # Ruta principal del dashboard
    path('tecnicos/', TecnicoListView.as_view(), name='tecnico-list'),  # Lista de técnicos
    path('tecnicos/nuevo/', TecnicoCreateView.as_view(), name='tecnico-create'),  # Formulario para agregar técnico
    path('tecnicos/editar/<int:pk>/', TecnicoUpdateView.as_view(), name='tecnico-update'),  # Actualizar técnico
    path('tecnicos/eliminar/<int:pk>/', TecnicoDeleteView.as_view(), name='tecnico-delete'),  # Eliminar técnico
]
