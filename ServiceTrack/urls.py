from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Ruta del admin
    path('admin/', admin.site.urls),

    # Ruta para incluir las URLs de la aplicación "servicios"
    path('', include('servicios.urls')),  # Esto incluye las URLs de tu aplicación principal
]