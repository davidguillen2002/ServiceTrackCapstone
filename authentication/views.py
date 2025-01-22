from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.contrib.auth import logout, authenticate, login
from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.messages import get_messages

class CustomLoginView(LoginView):
    template_name = 'authentication/login.html'  # Asegúrate de tener esta plantilla
    redirect_authenticated_user = True  # Redirige si ya está autenticado

    def get_success_url(self):
        # Redirige a la vista home, que según el rol redirigirá al lugar adecuado
        return reverse_lazy('home')

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('login')  # Redirige al login después del logout


def custom_login_view(request):
    # Limpiar mensajes residuales
    storage = get_messages(request)
    for _ in storage:
        pass  # Vacía los mensajes existentes

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('home')  # Redirige al home
        else:
            # Registrar un mensaje de error
            messages.error(request, 'Nombre de usuario o contraseña incorrectos.')

    return render(request, 'authentication/login.html')

def logout_view(request):
    storage = get_messages(request)  # Obtén los mensajes almacenados
    for _ in storage:
        pass  # Itera sobre los mensajes para limpiarlos

    logout(request)  # Cierra la sesión del usuario
    return redirect('login')  # Redirige a la página de inicio de sesión