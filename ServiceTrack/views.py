# ServiceTrack/views.py
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required

@login_required
def home_view(request):
    """Redirige al usuario a su vista principal según el rol."""
    user_role = request.user.rol.nombre.lower()

    if user_role == "administrador":
        return redirect('dashboard')
    elif user_role == "tecnico":
        return redirect('tecnico_dashboard')
    elif user_role == "cliente":
        return redirect('cliente_dashboard')
    else:
        return render(request, 'error.html', {'message': 'Rol desconocido.'})