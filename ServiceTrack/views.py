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
        return redirect('admin_dashboard')  # Cambiamos a 'admin_dashboard' que apunta a la URL correcta
    elif user_role == "tecnico":
        return redirect('tecnico_home')
    elif user_role == "cliente":
        return redirect('cliente_home')
    else:
        return redirect('logout')

@login_required
def admin_dashboard_view(request):
    """Vista del dashboard para el administrador."""
    return render(request, 'dashboard/dashboard.html')  # Asegúrate de que esta plantilla existe

@login_required
def tecnico_home_view(request):
    """Vista principal para técnicos."""
    return render(request, 'service_track/tecnico_home.html')

@login_required
def cliente_home_view(request):
    """Vista principal para clientes."""
    return render(request, 'service_track/cliente_home.html')