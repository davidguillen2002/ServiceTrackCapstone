from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from ServiceTrack.models import Usuario, Rol
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django import forms

@login_required
def dashboard_view(request):
    """Vista del dashboard."""
    return render(request, 'dashboard/knowledge_dashboard.html')

class TecnicoForm(forms.ModelForm):
    """Formulario personalizado para técnicos."""
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
        }

class TecnicoCreateForm(forms.ModelForm):
    """Formulario para crear un técnico con campo de contraseña."""
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
        }

class TecnicoUpdateForm(forms.ModelForm):
    """Formulario para actualizar un técnico sin el campo de contraseña."""
    class Meta:
        model = Usuario
        fields = ['nombre', 'username', 'rol', 'cedula', 'correo', 'celular']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Juan Pérez'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'jperez'}),
            'cedula': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1234567890'}),
            'correo': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'juan.perez@example.com'}),
            'celular': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '555-1234'}),
        }

class TecnicoCreateView(SuccessMessageMixin, CreateView):
    """Vista para crear un nuevo técnico."""
    model = Usuario
    form_class = TecnicoCreateForm  # Usamos el formulario de creación
    template_name = 'tecnico/tecnico_form.html'
    success_url = reverse_lazy('tecnico-list')
    success_message = "Técnico agregado correctamente."

    def form_valid(self, form):
        """Cifra la contraseña antes de guardar."""
        tecnico = form.save(commit=False)
        tecnico.password = make_password(form.cleaned_data['password'])  # Cifrado de la contraseña
        tecnico.save()
        return super().form_valid(form)

class TecnicoUpdateView(SuccessMessageMixin, UpdateView):
    """Vista para actualizar un técnico sin necesidad de cambiar la contraseña."""
    model = Usuario
    form_class = TecnicoUpdateForm  # Usamos el formulario de actualización
    template_name = 'tecnico/tecnico_form.html'
    success_url = reverse_lazy('tecnico-list')
    success_message = "Técnico actualizado correctamente."

class TecnicoListView(ListView):
    """Vista para listar todos los técnicos."""
    model = Usuario
    template_name = 'tecnico/tecnico_list.html'
    context_object_name = 'tecnicos'

class TecnicoDeleteView(SuccessMessageMixin, DeleteView):
    """Vista para eliminar un técnico."""
    model = Usuario
    template_name = 'tecnico/tecnico_confirm_delete.html'
    success_url = reverse_lazy('tecnico-list')
    success_message = "Técnico eliminado correctamente."
