from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


# Manager para el modelo Usuario
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

        if 'rol' not in extra_fields:
            try:
                admin_role = Rol.objects.get(nombre="administrador")
                extra_fields['rol'] = admin_role
            except Rol.DoesNotExist:
                raise ValueError(
                    "Debes crear el rol 'administrador' en la base de datos antes de crear un superusuario."
                )

        return self.create_user(username, password, **extra_fields)


# Modelo Rol
class Rol(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre


# Modelo Usuario
class Usuario(AbstractBaseUser, PermissionsMixin):
    nombre = models.CharField(max_length=100)
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=255)
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE)
    cedula = models.CharField(max_length=20, unique=True)
    correo = models.EmailField(max_length=100)
    celular = models.CharField(max_length=20)
    puntos = models.IntegerField(default=0)  # Solo los técnicos usan puntos
    medallas = models.ManyToManyField('Medalla', blank=True, related_name="tecnico")  # Medallas asociadas a técnicos
    servicios_completados = models.IntegerField(default=0)
    calificacion_promedio = models.FloatField(default=0.0)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UsuarioManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.nombre

    def calcular_promedio_tiempo_servicio(self):
        servicios = Servicio.objects.filter(tecnico=self, estado="completado")
        if servicios.exists():
            total_dias = sum((servicio.fecha_fin - servicio.fecha_inicio).days for servicio in servicios if servicio.fecha_fin)
            return total_dias / servicios.count()
        return None

    def servicios_con_baja_calificacion(self):
        return Servicio.objects.filter(tecnico=self, calificacion__lt=3).count()

class Notificacion(models.Model):
    TIPO_NOTIFICACION = [
        ('nuevo_servicio', 'Nuevo Servicio Asignado'),
        ('servicio_completado', 'Servicio Completado'),
        ('reto_asignado', 'Nuevo Reto Asignado'),
        ('actualizacion_reporte', 'Actualización de Reporte'),
        ('nueva_observacion', 'Nueva Observación en un Incidente'),
        ('nuevo_equipo', 'Nuevo Equipo Registrado'),
    ]

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='notificaciones')
    tipo = models.CharField(max_length=30, choices=TIPO_NOTIFICACION)
    mensaje = models.TextField()
    fecha_creacion = models.DateTimeField(default=timezone.now)
    leido = models.BooleanField(default=False)

    class Meta:
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Notificación {self.tipo} para {self.usuario.username}"

    @classmethod
    def crear_notificacion(cls, usuario, tipo, mensaje):
        """
        Crea una notificación y envía un mensaje al WebSocket.
        """
        notificacion = cls.objects.create(usuario=usuario, tipo=tipo, mensaje=mensaje)

        # Enviar notificación al WebSocket
        channel_layer = get_channel_layer()
        try:
            async_to_sync(channel_layer.group_send)(
                f"notificaciones_{usuario.id}",
                {
                    "type": "send_notification",
                    "data": {
                        "id": notificacion.id,
                        "tipo": tipo,
                        "mensaje": mensaje,
                        "leido": notificacion.leido,
                        "fecha_creacion": notificacion.fecha_creacion.strftime("%Y-%m-%d %H:%M:%S"),
                    },
                }
            )
            print(f"Mensaje enviado al grupo: notificaciones_{usuario.id}")
        except Exception as e:
            print(f"Error enviando mensaje al grupo WebSocket: {e}")

        return notificacion

    @staticmethod
    def obtener_notificaciones_por_rol(usuario):
        """
        Devuelve las notificaciones filtradas por el rol del usuario.

        - Técnicos: Todas las notificaciones relacionadas con su trabajo.
        - Administradores: Notificaciones de tipo "nuevo_servicio" o "servicio_completado".
        - Otros roles: Ninguna notificación (ajustable según necesidades).
        """
        if usuario.rol.nombre == "tecnico":
            return Notificacion.objects.filter(usuario=usuario)
        elif usuario.rol.nombre == "administrador":
            return Notificacion.objects.filter(tipo__in=["nuevo_servicio", "servicio_completado"])
        else:
            return Notificacion.objects.none()

# Modelo Equipo
class Equipo(models.Model):
    cliente = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    anio = models.IntegerField()
    tipo_equipo = models.CharField(max_length=50)
    observaciones = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.marca} {self.modelo} ({self.anio})"


# Modelo Servicio
class Servicio(models.Model):
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE)
    tecnico = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='tecnico_servicios',
        limit_choices_to={'rol__nombre': 'tecnico'}
    )
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
    diagnostico_inicial = models.TextField(null=True, blank=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['-fecha_inicio']

    def __str__(self):
        return f"Servicio {self.id} - {self.equipo}"

class Repuesto(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2)
    proveedor = models.CharField(max_length=100, blank=True, null=True)
    cantidad = models.PositiveIntegerField(default=1)
    servicio = models.ForeignKey(
        Servicio,
        on_delete=models.CASCADE,
        related_name='repuestos'
    )

    def __str__(self):
        return f"{self.nombre} - {self.servicio.equipo.marca} {self.servicio.equipo.modelo}"

# Modelo Categoria
class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre


# Modelo Guia
class Guia(models.Model):
    titulo = models.CharField(max_length=255)
    descripcion = models.TextField()
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    manual = models.TextField(null=True, blank=True)
    video = models.TextField(null=True, blank=True)
    tipo_servicio = models.CharField(max_length=100, null=True, blank=True)
    equipo_marca = models.CharField(max_length=100, null=True, blank=True)
    equipo_modelo = models.CharField(max_length=100, null=True, blank=True)
    puntuacion = models.FloatField(default=0)

    def __str__(self):
        return self.titulo

class ObservacionIncidente(models.Model):
    servicio = models.ForeignKey(
        Servicio,
        on_delete=models.CASCADE,
        related_name="observaciones",
        null=True,  # Opcional si no todas las observaciones están asociadas a un servicio
        blank=True
    )
    autor = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    descripcion = models.TextField()
    tipo_observacion = models.CharField(max_length=100)
    comentarios = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=50)
    fecha_reportada = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Observacion {self.id} - {self.tipo_observacion}"

# Modelo Enlace
class Enlace(models.Model):
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='enlaces')
    enlace = models.TextField()
    descripcion = models.TextField()

    def __str__(self):
        return f"Enlace {self.id} para Servicio {self.servicio.id}"


# Modelos para Gamificación

class Medalla(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    icono = models.ImageField(upload_to='medallas/', null=True, blank=True)
    puntos_necesarios = models.IntegerField()

    def __str__(self):
        return self.nombre


class Reto(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    puntos_otorgados = models.IntegerField()
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
    descripcion = models.TextField()

    def __str__(self):
        return f"{self.usuario} - {self.puntos_obtenidos} puntos en {self.fecha}"


# Modelo HistorialReporte
class HistorialReporte(models.Model):
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    tipo_reporte = models.CharField(max_length=10, choices=[('PDF', 'PDF'), ('Excel', 'Excel')])
    generado_por = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='reportes/', null=True, blank=True)

    def __str__(self):
        return f"{self.tipo_reporte} generado por {self.generado_por} el {self.fecha_generacion}"