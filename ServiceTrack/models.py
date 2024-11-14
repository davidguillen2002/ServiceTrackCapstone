# ServiceTrack/models.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.auth import get_user_model


class UsuarioManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("El usuario debe tener un nombre de usuario")
        if 'rol' not in extra_fields:
            raise ValueError("El rol es requerido para crear un usuario")

        user = self.model(username=username, **extra_fields)
        user.set_password(password)  # Encripta la contraseña
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        # Establece un rol por defecto para el superusuario si no se proporciona uno
        if 'rol' not in extra_fields:
            try:
                admin_role = Rol.objects.get(nombre="administrador")
                extra_fields['rol'] = admin_role
            except Rol.DoesNotExist:
                raise ValueError(
                    "Debes crear el rol 'administrador' en la base de datos antes de crear un superusuario."
                )

        return self.create_user(username, password, **extra_fields)

class Rol(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre

class Usuario(AbstractBaseUser, PermissionsMixin):
    nombre = models.CharField(max_length=100)
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=255)
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE)
    cedula = models.CharField(max_length=20, unique=True)
    correo = models.EmailField(max_length=100)
    celular = models.CharField(max_length=20)
    puntos = models.IntegerField(default=0)  # Solo los técnicos usan puntos
    medallas = models.ManyToManyField('Medalla', blank=True, related_name="usuarios")

    # Campos requeridos por AbstractBaseUser y PermissionsMixin
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UsuarioManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.nombre

class Equipo(models.Model):
    cliente = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    anio = models.IntegerField()
    tipo_equipo = models.CharField(max_length=50)
    observaciones = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.marca} {self.modelo} ({self.anio})"

class Servicio(models.Model):
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE)
    tecnico = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='tecnico_servicios')
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    estado = models.CharField(
        max_length=20,
        choices=[
            ('pendiente', 'Pendiente'),
            ('en_progreso', 'En Progreso'),
            ('completado', 'Completado')
        ],
        default='pendiente'
    )
    calificacion = models.IntegerField(null=True, blank=True)
    comentario_cliente = models.TextField(null=True, blank=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Servicio {self.id} - {self.equipo}"

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

class Guia(models.Model):
    titulo = models.CharField(max_length=255)
    descripcion = models.TextField()
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    manual = models.TextField(null=True, blank=True)  # Asumiendo que es un enlace o texto
    video = models.TextField(null=True, blank=True)
    tipo_servicio = models.CharField(max_length=100, null=True, blank=True)
    equipo_marca = models.CharField(max_length=100, null=True, blank=True)
    equipo_modelo = models.CharField(max_length=100, null=True, blank=True)
    puntuacion = models.FloatField(default=0)

    def __str__(self):
        return self.titulo

class ObservacionIncidente(models.Model):
    autor = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    descripcion = models.TextField()
    tipo_observacion = models.CharField(max_length=100)
    comentarios = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=50)
    fecha_reportada = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Observacion {self.id} - {self.tipo_observacion}"

class Enlace(models.Model):
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE)
    enlace = models.TextField()
    descripcion = models.TextField()

    def __str__(self):
        return f"Enlace {self.id} para Servicio {self.servicio.id}"

# Modelos adicionales para gamificación

class Medalla(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    icono = models.ImageField(upload_to='medallas/', null=True, blank=True)  # Campo opcional para icono de medalla
    puntos_necesarios = models.IntegerField()  # Puntos necesarios para obtener la medalla

    def __str__(self):
        return self.nombre

class Reto(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    puntos_otorgados = models.IntegerField()  # Puntos al completar el reto
    requisito = models.IntegerField(help_text="Ejemplo: cantidad de servicios completados o puntos a alcanzar")
    completado_por = models.ManyToManyField('Usuario', through='RetoUsuario', related_name='retos_completados')

    def __str__(self):
        return self.nombre

class RetoUsuario(models.Model):
    usuario = models.ForeignKey('Usuario', on_delete=models.CASCADE)
    reto = models.ForeignKey('Reto', on_delete=models.CASCADE)
    fecha_completado = models.DateTimeField(null=True, blank=True)
    cumplido = models.BooleanField(default=False)

class RegistroPuntos(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    puntos_obtenidos = models.IntegerField()
    fecha = models.DateTimeField(auto_now_add=True)
    descripcion = models.TextField()  # Ejemplo: "Completó un servicio", "Obtuvo una medalla", etc.

    def __str__(self):
        return f"{self.usuario} - {self.puntos_obtenidos} puntos en {self.fecha}"

# Modelo para almacenar el historial de reportes generados
class HistorialReporte(models.Model):
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    tipo_reporte = models.CharField(max_length=10, choices=[('PDF', 'PDF'), ('Excel', 'Excel')])
    generado_por = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='reportes/', null=True, blank=True)

    def __str__(self):
        return f"{self.tipo_reporte} generado por {self.generado_por} el {self.fecha_generacion}"