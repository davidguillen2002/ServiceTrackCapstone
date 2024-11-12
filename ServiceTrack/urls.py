# ServiceTrack/urls.py
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),  # Define 'home' aquí para evitar el NoReverseMatch
    path('admin/', admin.site.urls),
    path('auth/', include('authentication.urls')),  # URLs personalizadas de autenticación
    path('dashboard/', include('dashboard.urls')),  # URLs de dashboard
    path('servicios/', include('servicios.urls')),  # URLs de servicios
    path('gamificacion/', include('gamificacion.urls')),  # URLs de gamificación
    path('seguimiento/', include('seguimiento.urls')),  # URLs de seguimiento

    # Rutas de inicio según el rol
    path('admin_dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('tecnico_home/', views.tecnico_home_view, name='tecnico_home'),
    path('cliente_home/', views.cliente_home_view, name='cliente_home'),

    # Rutas de autenticación predeterminadas de Django
    path('accounts/', include('django.contrib.auth.urls')),  # Incluye las URLs de autenticación predeterminadas
]
