from django.contrib import admin
from django.urls import path, include
from . import views  # Importa las vistas de inicio de rol

urlpatterns = [
    path('', views.home_view, name='home'),  # Redirige a la vista principal según el rol
    path('admin/', admin.site.urls),
    path('auth/', include('authentication.urls')),  # Para el login y autenticación
    path('dashboard/', include('dashboard.urls')),  # URLs de dashboards para todos los roles
    path('servicios/', include('servicios.urls')),  # URLs de servicios
    path('gamificacion/', include('gamificacion.urls')),  # URLs de gamificación
    path('seguimiento/', include('seguimiento.urls')),  # URLs de seguimiento
    path('reportes/', include('reportes.urls')),  # URLs de reportes
    path('notificaciones/', include('notificaciones.urls')),  # URLs de notificaciones
]