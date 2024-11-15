"""
URL configuration for ServiceTrack project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# ServiceTrack/urls.py
from django.contrib import admin
from django.urls import path, include
from . import views  # Importa las vistas de inicio de rol

urlpatterns = [
    path('', views.home_view, name='home'),  # Redirige a la vista principal según el rol
    path('admin/', admin.site.urls),
    path('auth/', include('authentication.urls')),  # Para el login y autenticación
    path('dashboard/', include('dashboard.urls')),  # URLs exclusivas de administración
    path('servicios/', include('servicios.urls')),  # URLs de servicios
    path('gamificacion/', include('gamificacion.urls')),  # URLs de gamificación
    path('seguimiento/', include('seguimiento.urls')),  # URLs de seguimiento
    path('reportes/', include('reportes.urls')), # URLs de reportes
    path('notificaciones/', include('notificaciones.urls')),

    # Vistas de inicio según el rol
    path('admin_dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('tecnico_home/', views.tecnico_home_view, name='tecnico_home'),
    path('cliente_home/', views.cliente_home_view, name='cliente_home'),
]

