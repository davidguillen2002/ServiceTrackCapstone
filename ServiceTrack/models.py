from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db.models import Avg, Sum
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import random
from django.core.exceptions import ValidationError
from django.utils.timezone import now

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
    """
    Modelo personalizado de usuario con campos de gamificación.
    """
    nombre = models.CharField(max_length=100)
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=255)
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE)
    cedula = models.CharField(max_length=20, unique=True)
    correo = models.EmailField(max_length=100)
    celular = models.CharField(max_length=20)

    # Campos de gamificación
    puntos = models.IntegerField(default=0, help_text="Puntos acumulados por el usuario.")
    experiencia = models.IntegerField(default=0, help_text="Experiencia actual del usuario.")
    nivel = models.IntegerField(default=1, help_text="Nivel actual del usuario.")
    servicios_completados = models.IntegerField(default=0, help_text="Total de servicios completados.")
    calificacion_promedio = models.FloatField(default=0.0, help_text="Calificación promedio acumulada.")

    # Relación con medallas
    medallas = models.ManyToManyField('Medalla', blank=True, related_name="tecnicos")

    # Campos para clientes
    servicios_solicitados = models.IntegerField(default=0, help_text="Número total de servicios solicitados por el cliente.")

    # Campos adicionales para autenticación
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # Manager
    objects = UsuarioManager()

    # Configuración del modelo
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.nombre

    def calcular_proximo_nivel_cliente(self):
        """
        Calcula los puntos necesarios para que el cliente suba de nivel.
        """
        return self.nivel_cliente * 200

    def verificar_y_actualizar_nivel_cliente(self):
        """
        Actualiza el nivel del cliente si cumple con los puntos necesarios.
        """
        while self.puntos_cliente >= self.calcular_proximo_nivel_cliente():
            self.puntos_cliente -= self.calcular_proximo_nivel_cliente()
            self.nivel_cliente += 1
            # Notificar al cliente sobre el nuevo nivel
            Notificacion.crear_notificacion(
                usuario=self,
                tipo="nivel_cliente",
                mensaje=f"¡Felicidades {self.nombre}, has alcanzado el nivel {self.nivel_cliente}! 🎉"
            )
        self.save()

    def calcular_progreso_nivel_por_retos(self):
        """
        Calcula el progreso del nivel actual del usuario basado en los retos completados.
        """
        temporada_actual = Temporada.obtener_temporada_actual()
        if not temporada_actual:
            return 0

        retos_nivel = RetoUsuario.objects.filter(
            usuario=self,
            reto__nivel=self.nivel,
            reto__temporada=temporada_actual
        )
        total_retos = retos_nivel.count()
        retos_cumplidos = retos_nivel.filter(cumplido=True).count()

        return round((retos_cumplidos / total_retos) * 100, 2) if total_retos > 0 else 0

    # Métodos de lógica del modelo
    def calcular_experiencia_nivel_siguiente(self):
        """
        Calcula la experiencia necesaria para alcanzar el siguiente nivel.
        Si ya está en el nivel máximo, retorna 0.
        """
        if self.nivel >= 5:
            return 0
        return 100 * self.nivel

    def subir_nivel(self):
        """
        Verifica si el usuario tiene suficiente experiencia para subir de nivel y ajusta los valores.
        Se asegura de que no se exceda del nivel máximo permitido.
        """
        from gamificacion.notifications import notificar_tecnico  # Importación local para evitar el ciclo

        experiencia_requerida = self.calcular_experiencia_nivel_siguiente()

        while self.experiencia >= experiencia_requerida and self.nivel < 5:  # Limitar al nivel máximo permitido
            self.experiencia -= experiencia_requerida
            self.nivel += 1
            experiencia_requerida = self.calcular_experiencia_nivel_siguiente()

            # Notificar al usuario sobre el nuevo nivel
            notificar_tecnico(
                usuario=self,
                mensaje=f"¡Felicidades {self.nombre}, alcanzaste el nivel {self.nivel}! 🎉",
                tipo="info"
            )

            # Asignar retos del nuevo nivel
            self.asignar_retos_por_nivel()

        if self.nivel >= 5:  # Si alcanza el nivel máximo, ajusta la experiencia sobrante
            self.experiencia = min(self.experiencia, 0)

        self.save()

    def calcular_experiencia_total(self):
        """
        Calcula la experiencia total del usuario considerando retos cumplidos y puntos directos.
        """
        temporada_actual = Temporada.obtener_temporada_actual()
        if not temporada_actual:
            return self.experiencia

        # Experiencia por retos cumplidos
        retos_cumplidos = RetoUsuario.objects.filter(
            usuario=self,
            cumplido=True,
            reto__temporada=temporada_actual
        )
        experiencia_por_retos = retos_cumplidos.aggregate(
            total=Sum('reto__puntos_otorgados')
        )['total'] or 0

        # Experiencia por puntos directos
        puntos_directos = RegistroPuntos.objects.filter(
            usuario=self,
            fecha__range=[temporada_actual.fecha_inicio, temporada_actual.fecha_fin]
        ).aggregate(total=Sum('puntos_obtenidos'))['total'] or 0

        return experiencia_por_retos + puntos_directos


    def calcular_progreso_nivel(self):
        """
        Calcula el porcentaje de progreso hacia el siguiente nivel.
        """
        experiencia_requerida = self.calcular_experiencia_nivel_siguiente()
        return round((self.experiencia / experiencia_requerida) * 100, 2)

    def otorgar_experiencia(usuario, cantidad):
        """
        Otorga experiencia al usuario, verifica si sube de nivel y ajusta retos asociados.
        """

        from gamificacion.notifications import notificar_tecnico  # Importación local para evitar el ciclo

        usuario.experiencia += cantidad
        while usuario.experiencia >= usuario.calcular_experiencia_nivel_siguiente() and usuario.nivel < 5:
            exceso = usuario.experiencia - usuario.calcular_experiencia_nivel_siguiente()
            usuario.nivel += 1
            usuario.experiencia = exceso

            # Notificar al usuario
            notificar_tecnico(
                usuario=usuario,
                mensaje=f"¡Felicidades {usuario.nombre}, alcanzaste el nivel {usuario.nivel}! 🎉",
                tipo="info"
            )
            usuario.asignar_retos_por_nivel()  # Asignar retos nuevos para el nivel actual

        if usuario.nivel >= 5:
            usuario.experiencia = max(usuario.experiencia, 0)  # Ajustar experiencia si alcanza el nivel máximo
        else:
            notificar_tecnico(
                usuario=usuario,
                mensaje=f"¡Felicidades {usuario.nombre}, alcanzaste el nivel {usuario.nivel}! 🎉",
                tipo="info"
            )

        usuario.save()

    def servicios_con_baja_calificacion(self):
        """
        Retorna el número de servicios con una calificación menor a 3.
        """
        return Servicio.objects.filter(tecnico=self, calificacion__lt=3).count()

    def calcular_promedio_tiempo_servicio(self):
        """
        Calcula el tiempo promedio que el usuario tarda en completar un servicio.
        """
        servicios = Servicio.objects.filter(tecnico=self, estado="completado")
        if servicios.exists():
            total_dias = sum((servicio.fecha_fin - servicio.fecha_inicio).days for servicio in servicios if servicio.fecha_fin)
            return total_dias / servicios.count()
        return None

    def actualizar_calificacion_promedio(self):
        """
        Actualiza la calificación promedio basada en servicios completados.
        """
        promedio = (
            Servicio.objects.filter(tecnico=self, estado="completado")
            .aggregate(promedio=Avg("calificacion"))["promedio"]
            or 0
        )
        self.calificacion_promedio = round(promedio, 2)
        self.save()

    def asignar_medalla(self, medalla):
        """
        Asigna una medalla al usuario si cumple con los requisitos.
        """
        if not self.medallas.filter(id=medalla.id).exists():
            self.medallas.add(medalla)
            self.save()

    def limpiar_medallas(self):
        """
        Remueve medallas si el usuario ya no cumple con los requisitos.
        """
        for medalla in self.medallas.all():
            if self.puntos < medalla.puntos_necesarios:
                self.medallas.remove(medalla)

    def puntos_totales(self):
        """
        Calcula el total de puntos obtenidos por el usuario.
        """
        return self.puntos

    def retos_actuales(self):
        """
        Retorna los retos asignados al usuario que corresponden a su nivel actual.
        """
        return RetoUsuario.objects.filter(
            usuario=self,
            reto__nivel=self.nivel,
            cumplido=False
        )

    def verificar_y_subir_nivel(self):
        """
        Verifica si el usuario tiene suficiente experiencia para subir de nivel.
        Reinicia la experiencia si se sube de nivel.
        """
        from gamificacion.notifications import notificar_tecnico  # Importación local para evitar el ciclo

        experiencia_requerida = self.calcular_experiencia_nivel_siguiente()

        while self.experiencia >= experiencia_requerida:
            exceso_experiencia = self.experiencia - experiencia_requerida

            # Incrementar nivel
            self.nivel += 1
            self.experiencia = exceso_experiencia

            # Asignar nuevos retos para el nivel actual
            self.asignar_retos_por_nivel()

            # Notificar al usuario
            notificar_tecnico(
                usuario=self,
                mensaje=f"¡Felicidades {self.nombre}, alcanzaste el nivel {self.nivel}! 🎉",
                tipo="info"
            )

            experiencia_requerida = self.calcular_experiencia_nivel_siguiente()

        # Reiniciar experiencia si se alcanza el nivel máximo
        if self.nivel >= 5:
            self.experiencia = 0

        self.save()

    def asignar_retos_por_nivel(self):
        """
        Asigna retos específicos al usuario según su nivel actual.
        Crea retos para el nivel actual del usuario y los asocia con él si no existen.
        """
        # Diccionario de retos por nivel
        retos_por_nivel = {
            1: [
                {"nombre": "Primer Servicio", "descripcion": "Completa tu primer servicio exitosamente.",
                 "puntos_otorgados": 50, "criterio": "servicios", "valor_objetivo": 1},
                {"nombre": "Calificación Inicial", "descripcion": "Obtén una calificación promedio mínima de 3.",
                 "puntos_otorgados": 30, "criterio": "calificaciones", "valor_objetivo": 3},
                {"nombre": "Acumula Puntos Básicos", "descripcion": "Acumula al menos 100 puntos.",
                 "puntos_otorgados": 20, "criterio": "puntos", "valor_objetivo": 100},
            ],
            2: [
                {"nombre": "Servicio Rápido", "descripcion": "Completa 10 servicios en menos de 7 días.",
                 "puntos_otorgados": 100, "criterio": "servicios", "valor_objetivo": 10},
                {"nombre": "Calificación Excelente", "descripcion": "Obtén una calificación promedio de al menos 4.",
                 "puntos_otorgados": 50, "criterio": "calificaciones", "valor_objetivo": 4},
                {"nombre": "Puntos Progresivos", "descripcion": "Acumula 200 puntos.", "puntos_otorgados": 40,
                 "criterio": "puntos", "valor_objetivo": 200},
            ],
            3: [
                {"nombre": "Avance Profesional", "descripcion": "Completa 20 servicios exitosos.",
                 "puntos_otorgados": 150, "criterio": "servicios", "valor_objetivo": 20},
                {"nombre": "Calificación Sobresaliente",
                 "descripcion": "Obtén una calificación promedio de al menos 4.5.", "puntos_otorgados": 70,
                 "criterio": "calificaciones", "valor_objetivo": 4.5},
                {"nombre": "Puntos Avanzados", "descripcion": "Acumula 500 puntos.", "puntos_otorgados": 80,
                 "criterio": "puntos", "valor_objetivo": 500},
            ],
            4: [
                {"nombre": "Técnico Experto", "descripcion": "Completa 30 servicios exitosos.", "puntos_otorgados": 200,
                 "criterio": "servicios", "valor_objetivo": 30},
                {"nombre": "Calificación Perfecta", "descripcion": "Obtén una calificación promedio de 4.6.",
                 "puntos_otorgados": 100, "criterio": "calificaciones", "valor_objetivo": 4.6},
                {"nombre": "Puntos Máximos", "descripcion": "Acumula 1000 puntos.", "puntos_otorgados": 120,
                 "criterio": "puntos", "valor_objetivo": 1000},
            ],
            5: [
                {"nombre": "Maestro Técnico", "descripcion": "Completa 50 servicios exitosos.", "puntos_otorgados": 300,
                 "criterio": "servicios", "valor_objetivo": 50},
                {"nombre": "Excelencia Continua",
                 "descripcion": "Mantén una calificación promedio de 4.8 o más en los últimos 10 servicios.",
                 "puntos_otorgados": 150, "criterio": "calificaciones", "valor_objetivo": 4.8},
                {"nombre": "Dominio Total", "descripcion": "Acumula 2000 puntos.", "puntos_otorgados": 200,
                 "criterio": "puntos", "valor_objetivo": 2000},
            ],
        }

        # Obtener retos para el nivel actual del usuario
        retos_nivel = retos_por_nivel.get(self.nivel, [])

        for reto_data in retos_nivel:
            # Crear o recuperar el reto existente
            reto, created = Reto.objects.get_or_create(
                nombre=reto_data["nombre"],
                defaults={
                    "descripcion": reto_data["descripcion"],
                    "puntos_otorgados": reto_data["puntos_otorgados"],
                    "criterio": reto_data["criterio"],
                    "valor_objetivo": reto_data["valor_objetivo"],
                    "nivel": self.nivel
                }
            )

            # Asociar el reto al usuario si no está ya asignado
            RetoUsuario.objects.get_or_create(
                usuario=self,
                reto=reto,
                defaults={"cumplido": False, "progreso": 0}
            )

            if created:
                print(f"[INFO] Reto '{reto.nombre}' creado para nivel {self.nivel}.")
            else:
                print(f"[INFO] Reto '{reto.nombre}' ya existe.")

    def clean(self):
        if Usuario.objects.filter(correo=self.correo).exclude(id=self.id).exists():
            raise ValidationError("El correo ya está registrado.")
        if not self.celular.isdigit() or len(self.celular) < 10:
            raise ValidationError("El número de celular debe tener al menos 10 dígitos.")
        super().clean()

    class Meta:
        ordering = ['-nivel', '-puntos']
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

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
    extra_data = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Notificación {self.tipo} para {self.usuario.username}"

    @classmethod
    def crear_notificacion(cls, usuario, tipo, mensaje):
        notificacion = cls.objects.create(usuario=usuario, tipo=tipo, mensaje=mensaje)
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"notificaciones_{usuario.id}",
            {
                "type": "send_notification",
                "data": {
                    "id": notificacion.id,
                    "tipo": tipo,
                    "mensaje": mensaje,
                    "fecha_creacion": notificacion.fecha_creacion.strftime("%Y-%m-%d %H:%M:%S"),
                },
            }
        )
        return notificacion

    @staticmethod
    def obtener_notificaciones_por_rol(usuario):
        if usuario.rol.nombre == "tecnico":
            return Notificacion.objects.filter(usuario=usuario)
        elif usuario.rol.nombre == "administrador":
            return Notificacion.objects.filter(tipo__in=["nuevo_servicio", "servicio_completado"])
        elif usuario.rol.nombre == "cliente":
            return Notificacion.objects.filter(usuario=usuario)
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
    codigo_entrega = models.CharField(max_length=6, null=True, blank=True)  # Código de validación único
    entrega_confirmada = models.BooleanField(default=False)  # Estado de confirmación de entrega

    class Meta:
        ordering = ['-fecha_inicio']

    def __str__(self):
        return f"Servicio {self.id} - {self.equipo}"

    def generar_codigo_entrega(self):
        self.codigo_entrega = str(random.randint(100000, 999999))  # Generar código de 6 dígitos
        self.save()

    @property
    def esta_completado(self):
        return self.estado == "completado"

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

# Modelo Temporada
class Temporada(models.Model):
    nombre = models.CharField(max_length=50, help_text="Ejemplo: Temporada 2025-I")
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    activa = models.BooleanField(default=True, help_text="Indica si la temporada está activa")
    usuarios_participantes = models.ManyToManyField(
        Usuario, through='EstadisticaTemporada', related_name='temporadas'
    )

    def __str__(self):
        return self.nombre

    @staticmethod
    def obtener_temporada_actual():
        """
        Retorna la temporada activa según la fecha actual.
        """
        fecha_actual = now().date()
        return Temporada.objects.filter(
            fecha_inicio__lte=fecha_actual,
            fecha_fin__gte=fecha_actual,
            activa=True
        ).first()

    @staticmethod
    def crear_temporadas_anuales():
        """
        Crea dos temporadas automáticamente para el siguiente año.
        """
        fecha_actual = now().date()
        anio = fecha_actual.year + 1

        Temporada.objects.create(
            nombre=f"Temporada {anio}-I",
            fecha_inicio=f"{anio}-01-01",
            fecha_fin=f"{anio}-06-30",
            activa=False
        )
        Temporada.objects.create(
            nombre=f"Temporada {anio}-II",
            fecha_inicio=f"{anio}-07-01",
            fecha_fin=f"{anio}-12-31",
            activa=False
        )

# Modelo Estadística por Temporada
class EstadisticaTemporada(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    temporada = models.ForeignKey(Temporada, on_delete=models.CASCADE)
    puntos_totales = models.IntegerField(default=0)
    nivel_alcanzado = models.IntegerField(default=0)
    retos_completados = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.usuario.nombre} - {self.temporada.nombre}"

class Medalla(models.Model):
    temporada = models.ForeignKey(Temporada, on_delete=models.CASCADE, related_name='medallas', null=True, blank=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    icono = models.ImageField(upload_to='medallas/', null=True, blank=True)
    puntos_necesarios = models.IntegerField()
    retos_asociados = models.ManyToManyField('Reto', blank=True, related_name='medallas_asociadas')
    nivel_requerido = models.IntegerField(default=1, help_text="Nivel mínimo requerido para obtener esta medalla.")  # Nuevo campo

    def asignar_si_cumple(self, usuario):
        """
        Verifica si un usuario cumple con los requisitos para esta medalla
        y la asigna si no la tiene.
        """
        retos_cumplidos = all(
            RetoUsuario.objects.filter(usuario=usuario, reto=reto, cumplido=True).exists()
            for reto in self.retos_asociados.all()
        )

        if (
            retos_cumplidos
            and usuario.puntos >= self.puntos_necesarios
            and usuario.nivel >= self.nivel_requerido
            and not usuario.medallas.filter(id=self.id).exists()
        ):
            usuario.medallas.add(self)
            usuario.save()

            # Registrar el logro en el historial de puntos
            RegistroPuntos.objects.create(
                usuario=usuario,
                puntos_obtenidos=0,
                descripcion=f"Medalla obtenida: {self.nombre}"
            )

            # Notificar al usuario
            Notificacion.crear_notificacion(
                usuario=usuario,
                tipo="reconocimiento",
                mensaje=f"¡Felicidades! Has obtenido la medalla: {self.nombre}"
            )

class Reto(models.Model):
    temporada = models.ForeignKey(Temporada, on_delete=models.CASCADE, related_name='retos')
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    puntos_otorgados = models.IntegerField()
    nivel = models.IntegerField(
        default=1,
        help_text="Nivel asociado al reto. Define el nivel necesario para desbloquear este reto."
    )  # Nuevo campo para nivel
    criterio = models.CharField(
        max_length=50,
        choices=[
            ('puntos', 'Alcanzar cierta cantidad de puntos'),
            ('servicios', 'Completar una cantidad de servicios'),
            ('calificaciones', 'Lograr una calificación promedio mínima'),
        ],
        help_text="Define cómo se valida el cumplimiento del reto."
    )
    valor_objetivo = models.IntegerField(help_text="Ejemplo: 500 puntos, 10 servicios, o calificación promedio de 4")
    completado_por = models.ManyToManyField('Usuario', through='RetoUsuario', related_name='retos_completados')

    def clean(self):
        """
        Validación del modelo Reto.
        """
        if self.puntos_otorgados <= 0:
            raise ValidationError("Los puntos otorgados deben ser mayores que 0.")
        if self.valor_objetivo <= 0:
            raise ValidationError("El valor objetivo debe ser mayor que 0.")
        if self.nivel <= 0:
            raise ValidationError("El nivel debe ser mayor que 0.")
        super().clean()

    def validar_cumplimiento(self, usuario):
        """
        Verifica si un usuario cumple con el criterio del reto.
        """
        if self.criterio == 'puntos' and usuario.puntos >= self.valor_objetivo:
            return True
        elif self.criterio == 'servicios' and usuario.servicios_completados >= self.valor_objetivo:
            return True
        elif self.criterio == 'calificaciones' and usuario.calificacion_promedio >= self.valor_objetivo:
            return True
        return False

    def __str__(self):
        return f"Reto: {self.nombre} (Nivel: {self.nivel}, Objetivo: {self.valor_objetivo})"

class RetoUsuario(models.Model):
    usuario = models.ForeignKey('Usuario', on_delete=models.CASCADE, related_name="retos_usuario")
    reto = models.ForeignKey('Reto', on_delete=models.CASCADE, related_name="retos_asignados")
    cumplido = models.BooleanField(default=False)
    progreso = models.FloatField(default=0, help_text="Progreso actual del usuario en el reto (en %).")
    cantidad_actual = models.FloatField(default=0, help_text="Progreso absoluto en el reto.")
    fecha_completado = models.DateTimeField(null=True, blank=True)

    def actualizar_progreso(self):
        """
        Actualiza el progreso basado en el criterio del reto.
        """
        if self.reto.criterio == "puntos":
            self.cantidad_actual = min(self.usuario.puntos, self.reto.valor_objetivo)
            self.progreso = min((self.cantidad_actual / self.reto.valor_objetivo) * 100, 100)
        elif self.reto.criterio == "servicios":
            self.cantidad_actual = Servicio.objects.filter(tecnico=self.usuario, estado="completado").count()
            self.progreso = min((self.cantidad_actual / self.reto.valor_objetivo) * 100, 100)
        elif self.reto.criterio == "calificaciones":
            promedio_calificacion = (
                Servicio.objects.filter(tecnico=self.usuario, estado="completado")
                .aggregate(promedio=Avg("calificacion"))["promedio"] or 0
            )
            self.cantidad_actual = round(promedio_calificacion, 2)
            self.progreso = 100 if promedio_calificacion >= self.reto.valor_objetivo else 0
        else:
            self.progreso = 0

        self.save()

    def verificar_cumplimiento(self):
        """
        Verifica si el reto está completo y actualiza su estado.
        """
        if self.progreso >= 100 and not self.cumplido:
            self.cumplido = True
            self.fecha_completado = now()
            self.save()

            # Otorgar puntos al usuario
            self.otorgar_puntos_usuario()

            # Asignar medallas relacionadas al reto
            for medalla in self.reto.medallas_asociadas.all():
                medalla.asignar_si_cumple(self.usuario)

    def otorgar_puntos_usuario(self):
        """
        Otorga los puntos del reto al usuario si está cumplido.
        """
        self.usuario.puntos += self.reto.puntos_otorgados
        self.usuario.save()

        # Registrar los puntos otorgados
        RegistroPuntos.objects.create(
            usuario=self.usuario,
            puntos_obtenidos=self.reto.puntos_otorgados,
            descripcion=f"Reto completado: {self.reto.nombre}"
        )

    def es_cercano_a_completar(self):
        """
        Retorna True si el progreso está por encima del 75%.
        """
        return self.progreso >= 75

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['usuario', 'reto'], name='unique_usuario_reto')
        ]

    def __str__(self):
        return f"{self.usuario.nombre} - {self.reto.nombre} (Progreso: {self.progreso}%)"

class RegistroPuntos(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    servicio = models.ForeignKey(Servicio, on_delete=models.SET_NULL, null=True, blank=True)  # Relación explícita
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

# Modelo Recompensa
class Recompensa(models.Model):
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="recompensas"
    )
    reto = models.ForeignKey(Reto, on_delete=models.CASCADE, related_name="recompensas_asignadas")
    temporada = models.ForeignKey(Temporada, on_delete=models.CASCADE, related_name="recompensas")
    tipo = models.CharField(max_length=50)
    puntos_necesarios = models.IntegerField()
    descripcion = models.TextField()
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    redimido = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.tipo} - {self.descripcion} ({'Redimido' if self.redimido else 'Disponible'})"


class ChatMessage(models.Model):
    user_message = models.TextField()
    bot_response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user_message[:30]} - {self.bot_response[:30]}"