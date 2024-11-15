# dashboard/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from ServiceTrack.models import Usuario
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.hashers import make_password
from django import forms

@login_required
def dashboard_view(request):
    """Vista del dashboard."""
    return render(request, 'dashboard/knowledge_dashboard.html')

class UsuarioForm(forms.ModelForm):
    """Formulario personalizado para usuarios."""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '********'}),
        label="Contraseña"
    )

    class Meta:
        model = Usuario
        fields = ['nombre', 'username', 'password', 'rol', 'cedula', 'correo', 'celular']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Juan Pérez'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'jperez'}),
            'cedula': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1234567890'}),
            'correo': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'juan.perez@example.com'}),
            'celular': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '555-1234'}),
            'rol': forms.Select(attrs={'class': 'form-control'}),
        }

class UsuarioCreateForm(UsuarioForm):
    """Formulario para crear un usuario con campo de contraseña."""

class UsuarioUpdateForm(forms.ModelForm):
    """Formulario para actualizar un usuario sin el campo de contraseña."""
    class Meta:
        model = Usuario
        fields = ['nombre', 'username', 'rol', 'cedula', 'correo', 'celular']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Juan Pérez'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'jperez'}),
            'cedula': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1234567890'}),
            'correo': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'juan.perez@example.com'}),
            'celular': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '555-1234'}),
            'rol': forms.Select(attrs={'class': 'form-control'}),
        }

class UsuarioCreateView(SuccessMessageMixin, CreateView):
    """Vista para crear un nuevo usuario."""
    model = Usuario
    form_class = UsuarioCreateForm
    template_name = 'usuarios/usuario_form.html'
    success_url = reverse_lazy('usuario-list')
    success_message = "Usuario agregado correctamente."

    def form_valid(self, form):
        """Cifra la contraseña antes de guardar."""
        usuario = form.save(commit=False)
        usuario.password = make_password(form.cleaned_data['password'])
        usuario.save()
        return super().form_valid(form)

class UsuarioUpdateView(SuccessMessageMixin, UpdateView):
    """Vista para actualizar un usuario sin necesidad de cambiar la contraseña."""
    model = Usuario
    form_class = UsuarioUpdateForm
    template_name = 'usuarios/usuario_form.html'
    success_url = reverse_lazy('usuario-list')
    success_message = "Usuario actualizado correctamente."

class UsuarioListView(ListView):
    """Vista para listar todos los usuarios."""
    model = Usuario
    template_name = 'usuarios/usuario_list.html'
    context_object_name = 'usuarios'

class UsuarioDeleteView(SuccessMessageMixin, DeleteView):
    """Vista para eliminar un usuario."""
    model = Usuario
    template_name = 'usuarios/usuario_confirm_delete.html'
    success_url = reverse_lazy('usuario-list')
    success_message = "Usuario eliminado correctamente."