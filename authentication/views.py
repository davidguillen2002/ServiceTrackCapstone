from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.contrib.auth import logout, authenticate, login
from django.shortcuts import redirect, render
from django.contrib import messages

class CustomLoginView(LoginView):
    template_name = 'authentication/login.html'  # Asegúrate de tener esta plantilla
    redirect_authenticated_user = True  # Redirige si ya está autenticado

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('login')  # Redirige al login después del logout

def custom_login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, 'Has iniciado sesión correctamente.')
            return redirect('dashboard')  # Redirige a tu página principal o dashboard
        else:
            messages.error(request, 'Nombre de usuario o contraseña incorrectos.')

    return render(request, 'authentication/login.html')

def logout_view(request):
    logout(request)
    return redirect('login')