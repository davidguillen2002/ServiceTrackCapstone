from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Vistas para técnicos
    path('perfil/', views.perfil_gamificacion, name='perfil_gamificacion'),
    path('retos/', views.explorar_retos, name='explorar_retos'),
    path('nuevo-ranking-global/', views.nuevo_ranking_global, name='nuevo_ranking_global'),
    path('historial-puntos-paginado/', views.historial_puntos_paginated, name='historial_puntos_paginated'),
    path('recompensas/', views.recompensas_disponibles, name='recompensas_disponibles'),
    path('redimir-recompensa/', views.redimir_recompensa, name='redimir_recompensa'),

    # Panel de administración
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard_gamificacion'),
    path('otorgar-puntos/', views.otorgar_puntos_view, name='otorgar_puntos'),
    path('administrar_gamificacion/', views.administrar_gamificacion, name='administrar_gamificacion'),

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

    # Rutas AJAX para creación de elementos
    path('ajax/crear-temporada/', views.crear_temporada_ajax, name='crear_temporada_ajax'),
    path('ajax/crear-reto/', views.crear_reto_ajax, name='crear_reto_ajax'),
    path('ajax/crear-recompensa/', views.crear_recompensa_ajax, name='crear_recompensa_ajax'),
    path('ajax/crear-medalla/', views.crear_medalla_ajax, name='crear_medalla_ajax'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)