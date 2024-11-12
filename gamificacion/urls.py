from django.urls import path
from . import views

urlpatterns = [
    # Vistas para técnicos
    path('perfil/', views.perfil_gamificacion, name='perfil_gamificacion'),
    path('retos/', views.retos_disponibles, name='retos_disponibles'),
    path('historial-puntos/', views.historial_puntos, name='historial_puntos'),

    # Panel de administración
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard_gamificacion'),
    path('otorgar-puntos/', views.otorgar_puntos_view, name='otorgar_puntos'),

    # CRUD para Guías
    path('guias/', views.lista_guias, name='lista_guias'),
    path('guias/crear/', views.crear_guia, name='crear_guia'),
    path('guias/editar/<int:guia_id>/', views.editar_guia, name='editar_guia'),
    path('guias/eliminar/<int:guia_id>/', views.eliminar_guia, name='eliminar_guia'),

    # CRUD para Observaciones
    path('observaciones/', views.lista_observaciones, name='lista_observaciones'),
    path('observaciones/crear/', views.crear_observacion, name='crear_observacion'),
    path('observaciones/editar/<int:observacion_id>/', views.editar_observacion, name='editar_observacion'),
    path('observaciones/eliminar/<int:observacion_id>/', views.eliminar_observacion, name='eliminar_observacion'),

    # CRUD para Retos (admin-only)
    path('retos/lista/', views.lista_retos, name='lista_retos'),
    path('retos/crear/', views.crear_reto, name='crear_reto'),
    path('retos/editar/<int:reto_id>/', views.editar_reto, name='editar_reto'),
    path('retos/eliminar/<int:reto_id>/', views.eliminar_reto, name='eliminar_reto'),

    # CRUD para Medallas (admin-only)
    path('medallas/', views.lista_medallas, name='lista_medallas'),
    path('medallas/crear/', views.crear_medalla, name='crear_medalla'),
    path('medallas/editar/<int:medalla_id>/', views.editar_medalla, name='editar_medalla'),
    path('medallas/eliminar/<int:medalla_id>/', views.eliminar_medalla, name='eliminar_medalla'),
]