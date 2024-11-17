# ServiceTrack/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from dashboard.views import dashboard_view

User = get_user_model()

@login_required
def home_view(request):
    """Redirige al usuario a su vista principal según el rol."""
    if not hasattr(request.user, 'rol') or not request.user.rol:
        return render(request, 'error.html', {'message': 'No tienes un rol asignado.'})

    user_role = request.user.rol.nombre.lower()

    if user_role == "administrador":
        return redirect('admin_dashboard')
    elif user_role == "tecnico":
        return redirect('tecnico_home')
    elif user_role == "cliente":
        return redirect('cliente_home')
    else:
        return render(request, 'error.html', {'message': 'Rol desconocido.'})


@login_required
def admin_dashboard_view(request):
    """Vista del dashboard para el administrador."""
    # Reutiliza la lógica de dashboard_view
    return dashboard_view(request)

@login_required
def tecnico_home_view(request):
    """Vista principal para técnicos."""
    return render(request, 'service_track/tecnico_home.html')

@login_required
def cliente_home_view(request):
    """Vista principal para clientes."""
    return render(request, 'service_track/cliente_home.html')