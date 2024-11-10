# ServiceTrack/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model

User = get_user_model()


@login_required
def home_view(request):
    """Redirige al usuario a su vista principal según el rol."""
    user_role = request.user.rol.nombre.lower()

    if user_role == "administrador":
        return redirect('admin_dashboard')  # Redirige al dashboard de administrador
    elif user_role == "tecnico":
        return redirect('tecnico_home')  # Redirige a la página principal del técnico
    elif user_role == "cliente":
        return redirect('cliente_home')  # Redirige a la página principal del cliente
    else:
        return redirect('logout')  # Si no tiene un rol válido, cierra la sesión


@login_required
def admin_dashboard_view(request):
    """Vista del dashboard para el administrador."""
    return render(request, 'dashboard/admin_dashboard.html')


@login_required
def tecnico_home_view(request):
    """Vista principal para técnicos."""
    return render(request, 'service_track/tecnico_home.html')


@login_required
def cliente_home_view(request):
    """Vista principal para clientes."""
    return render(request, 'service_track/cliente_home.html')