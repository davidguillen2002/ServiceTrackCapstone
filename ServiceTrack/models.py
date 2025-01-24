from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db.models import Avg, Sum
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import random
from django.core.exceptions import ValidationError
from django.utils.timezone import now
import re

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

    def actualizar_estadisticas(self):
        """
        Actualiza estadísticas del técnico, incluyendo calificación promedio y servicios completados.
        """
        # Calcular servicios completados
        servicios_completados = Servicio.objects.filter(
            tecnico=self,
            estado="completado"
        ).count()
        self.servicios_completados = servicios_completados

        # Calcular calificación promedio
        promedio = Servicio.objects.filter(
            tecnico=self,
            estado="completado"
        ).aggregate(promedio=Avg("calificacion"))["promedio"] or 0
        self.calificacion_promedio = round(promedio, 2)

        self.save()

    def servicios_en_temporada(self, temporada):
        """
        Obtiene los servicios completados dentro del intervalo de la temporada.
        """
        return Servicio.objects.filter(
            tecnico=self,
            estado="completado",
            fecha_fin__range=(temporada.fecha_inicio, temporada.fecha_fin)
        )

    def calificacion_promedio_temporada(self, temporada):
        """
        Calcula el promedio de calificaciones de los servicios completados
        dentro del rango de fechas de la temporada.
        """
        servicios_temporada = Servicio.objects.filter(
            tecnico=self,
            estado="completado",
            fecha_fin__range=(temporada.fecha_inicio, temporada.fecha_fin)
        )
        promedio = servicios_temporada.aggregate(
            promedio=Avg('calificacion')
        )['promedio'] or 0
        return round(promedio, 2)

    def puntos_en_temporada(self, temporada):
        """
        Obtiene la suma de puntos obtenidos dentro del intervalo de la temporada.
        """
        return RegistroPuntos.objects.filter(
            usuario=self,
            fecha__range=(temporada.fecha_inicio, temporada.fecha_fin)
        ).aggregate(total=Sum('puntos_obtenidos'))['total'] or 0

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
        experiencia_requerida = self.calcular_experiencia_nivel_siguiente()

        while self.experiencia >= experiencia_requerida and self.nivel < 5:  # Limitar al nivel máximo permitido
            self.experiencia -= experiencia_requerida
            self.nivel += 1
            experiencia_requerida = self.calcular_experiencia_nivel_siguiente()

            # Crear notificación para el usuario
            Notificacion.crear_notificacion(
                usuario=self,
                tipo="nivel_cliente",
                mensaje=f"¡Felicidades {self.nombre}, has alcanzado el nivel {self.nivel}! 🎉"
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

    def convertir_experiencia_a_puntos(self):
        """
        Convierte experiencia acumulada en puntos redimibles.
        Ratio: 10 experiencia = 20 puntos.
        Verifica si ya se realizó la conversión para evitar duplicidad.
        """
        # Verificar si ya se procesó la conversión de experiencia hoy
        conversion_existente = RegistroPuntos.objects.filter(
            usuario=self,
            es_conversion_experiencia=True,
            fecha__date=now().date()
        ).exists()

        if conversion_existente:
            return 0  # No realizar conversión si ya se procesó hoy

        # Proceso de conversión
        if self.experiencia >= 10:  # Ratio: 10 experiencia = 20 puntos
            puntos_convertidos = (self.experiencia // 10) * 20  # 10 experiencia -> 20 puntos
            self.experiencia %= 10  # Mantener el remanente como experiencia
            self.puntos += puntos_convertidos
            self.save()

            # Registrar conversión
            RegistroPuntos.objects.create(
                usuario=self,
                puntos_obtenidos=puntos_convertidos,
                descripcion="Conversión de experiencia a puntos",
                es_conversion_experiencia=True
            )
            return puntos_convertidos
        return 0

    def actualizar_puntos_totales(self):
        """
        Calcula y actualiza el total de puntos considerando la experiencia convertida.
        """
        self.convertir_experiencia_a_puntos()  # Asegura la conversión de experiencia a puntos
        self.save()

    def clean(self):
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

    @property
    def display_text(self):
        if self.cliente:
            return f"{self.marca} {self.modelo} - {self.cliente.nombre} - {self.cliente.cedula}"
        return f"{self.marca} {self.modelo} - Sin Cliente"

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
    calificacion = models.DecimalField(
        max_digits=3, decimal_places=1, null=True, blank=True, help_text="Calificación de 1 a 5, admite decimales"
    )
    comentario_cliente = models.TextField(null=True, blank=True)
    diagnostico_inicial = models.TextField(null=True, blank=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    codigo_entrega = models.CharField(max_length=6, null=True, blank=True)  # Código de validación único
    entrega_confirmada = models.BooleanField(default=False)  # Estado de confirmación de entrega

    class Meta:
        ordering = ['-fecha_inicio']

    def save(self, *args, **kwargs):
        # Validar si la fecha de finalización está dentro de la temporada activa
        if self.fecha_fin:
            temporada_actual = Temporada.obtener_temporada_actual()
            if temporada_actual and not (temporada_actual.fecha_inicio <= self.fecha_fin <= temporada_actual.fecha_fin):
                raise ValidationError(
                    "La fecha de finalización del servicio debe estar dentro de la temporada activa."
                )

        super().save(*args, **kwargs)

        # Actualizar estadísticas del técnico al guardar un servicio completado
        if self.estado == "completado" and self.calificacion is not None:
            self.tecnico.actualizar_estadisticas()

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

class TipoObservacion(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre


class ObservacionIncidente(models.Model):
    servicio = models.ForeignKey(
        Servicio,
        on_delete=models.CASCADE,
        related_name="observaciones",
        null=True,
        blank=True
    )
    autor = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    descripcion = models.TextField()
    tipo_observacion = models.ForeignKey(
        TipoObservacion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="observaciones"
    )
    comentarios = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=50)
    fecha_reportada = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Observación {self.id} - {self.tipo_observacion.nombre if self.tipo_observacion else 'Sin tipo'}"


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
    )
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
    completado_por = models.ManyToManyField(
        'Usuario',
        through='RetoUsuario',  # Relación explícita al modelo intermedio
        related_name='retos_completados'
    )

    def clean(self):
        if self.puntos_otorgados <= 0:
            raise ValidationError("Los puntos otorgados deben ser mayores que 0.")
        if self.valor_objetivo <= 0:
            raise ValidationError("El valor objetivo debe ser mayor que 0.")
        if self.nivel <= 0:
            raise ValidationError("El nivel debe ser mayor que 0.")
        super().clean()

    def validar_cumplimiento(self, usuario):
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
        Asegura que el cálculo de calificaciones considere solo la temporada actual.
        """
        temporada_actual = Temporada.obtener_temporada_actual()
        if not temporada_actual:
            self.progreso = 0
            self.save()
            return

        if self.reto.criterio == "puntos":
            puntos_temporada = RegistroPuntos.objects.filter(
                usuario=self.usuario,
                fecha__range=(temporada_actual.fecha_inicio, temporada_actual.fecha_fin)
            ).aggregate(total=Sum('puntos_obtenidos'))['total'] or 0
            self.cantidad_actual = min(puntos_temporada, self.reto.valor_objetivo)
            self.progreso = min((self.cantidad_actual / self.reto.valor_objetivo) * 100, 100)

        elif self.reto.criterio == "servicios":
            servicios_temporada = Servicio.objects.filter(
                tecnico=self.usuario,
                estado="completado",
                fecha_fin__range=(temporada_actual.fecha_inicio, temporada_actual.fecha_fin)
            ).count()
            self.cantidad_actual = servicios_temporada
            self.progreso = min((self.cantidad_actual / self.reto.valor_objetivo) * 100, 100)

        elif self.reto.criterio == "calificaciones":
            promedio_calificacion = Servicio.objects.filter(
                tecnico=self.usuario,
                estado="completado",
                fecha_fin__range=(temporada_actual.fecha_inicio, temporada_actual.fecha_fin)
            ).aggregate(promedio=Avg("calificacion"))["promedio"] or 0
            self.cantidad_actual = round(promedio_calificacion, 2)
            self.progreso = 100 if promedio_calificacion >= self.reto.valor_objetivo else 0

        else:
            self.progreso = 0

        self.save()

    def verificar_cumplimiento(self):
        """
        Verifica si el reto está completo, actualiza su estado y otorga la recompensa asociada.
        """
        if self.progreso >= 100 and not self.cumplido:
            self.cumplido = True
            self.fecha_completado = now()
            self.save()

            # Otorgar puntos al usuario
            self.usuario.puntos += self.reto.puntos_otorgados
            self.usuario.save()

            # Registrar puntos otorgados
            RegistroPuntos.objects.create(
                usuario=self.usuario,
                puntos_obtenidos=self.reto.puntos_otorgados,
                descripcion=f"Reto completado: {self.reto.nombre}"
            )

            # Otorgar la recompensa asociada al reto
            if hasattr(self.reto, 'recompensa'):
                recompensa = self.reto.recompensa
                recompensa.verificar_y_otorgar(self.usuario)

            # Notificar al usuario
            from gamificacion.notifications import notificar_tecnico
            notificar_tecnico(
                usuario=self.usuario,
                mensaje=f"¡Has completado el reto '{self.reto.nombre}' y recibido tu recompensa! 🎉",
                tipo="success"
            )

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
    servicio = models.ForeignKey(Servicio, on_delete=models.SET_NULL, null=True, blank=True)
    puntos_obtenidos = models.IntegerField()
    fecha = models.DateTimeField(auto_now_add=True)
    descripcion = models.TextField()
    es_conversion_experiencia = models.BooleanField(default=False)  # Nuevo campo

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

class Recompensa(models.Model):
    temporada = models.ForeignKey(
        'Temporada',
        on_delete=models.CASCADE,
        related_name="recompensas",
        help_text="Temporada a la que pertenece esta recompensa."
    )
    descripcion = models.TextField(help_text="Descripción detallada de la recompensa.")
    valor = models.DecimalField(max_digits=10, decimal_places=2, help_text="Valor monetario o simbólico asociado a la recompensa.")
    puntos_necesarios = models.IntegerField(help_text="Cantidad de puntos requeridos para redimir esta recompensa.")
    tipo = models.CharField(max_length=50, help_text="Tipo de recompensa: bono, herramienta o trofeo.")
    reto = models.OneToOneField(
        'Reto',
        on_delete=models.SET_NULL,
        related_name="recompensa",
        null=True,
        blank=True,
        help_text="Reto asociado directamente a esta recompensa (opcional)."
    )
    usuarios_redimidos = models.ManyToManyField(
        'Usuario',
        through='RecompensaUsuario',
        related_name="recompensas_redimidas",
        blank=True,
        help_text="Usuarios que han redimido esta recompensa."
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['reto'], name='unique_recompensa_por_reto')
        ]
        ordering = ['temporada', 'tipo']
        verbose_name = "Recompensa"
        verbose_name_plural = "Recompensas"

    def __str__(self):
        return f"{self.tipo}: {self.descripcion} - Temporada: {self.temporada.nombre}"

    def verificar_y_otorgar(self, usuario):
        """
        Verifica si la recompensa puede ser otorgada al usuario y realiza el registro si es aplicable.
        """
        # Verificar si el usuario ya tiene esta recompensa
        recompensa_usuario = RecompensaUsuario.objects.filter(usuario=usuario, recompensa=self).exists()
        if not recompensa_usuario:
            # Crear la relación entre el usuario y la recompensa
            RecompensaUsuario.objects.create(usuario=usuario, recompensa=self)
            print(f"[INFO] Recompensa '{self.descripcion}' otorgada al usuario '{usuario.username}'.")
        else:
            print(f"[INFO] El usuario '{usuario.username}' ya tiene la recompensa '{self.descripcion}'.")



class RecompensaUsuario(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="recompensas_usuario")
    recompensa = models.ForeignKey(Recompensa, on_delete=models.CASCADE, related_name="usuarios_asignados")
    redimido = models.BooleanField(default=False, help_text="Indica si el usuario ya redimió esta recompensa.")
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    fecha_redencion = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('usuario', 'recompensa')
        verbose_name = "Recompensa de Usuario"
        verbose_name_plural = "Recompensas de Usuarios"

    def __str__(self):
        return f"{self.usuario.nombre} - {self.recompensa.descripcion} - Redimido: {self.redimido}"


class ChatMessage(models.Model):
    user = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name="chat_messages",
        help_text="Usuario asociado al mensaje."
    )
    user_message = models.TextField(help_text="Mensaje enviado por el usuario.")
    bot_response = models.TextField(help_text="Respuesta generada por el bot en HTML.")
    raw_response = models.TextField(
        null=True, blank=True,
        help_text="Respuesta original generada por el bot en formato Markdown."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat de {self.user.nombre} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"

class Capacitacion(models.Model):
    titulo = models.CharField(max_length=255)
    descripcion_corta = models.TextField(max_length=500)
    link = models.URLField()

    def __str__(self):
        return self.titulo

    def clean(self):
        """
        Valida que el enlace proporcionado sea un enlace válido de YouTube.
        """
        if not re.match(r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/(watch\?v=|embed/)?[a-zA-Z0-9_-]{11}', self.link):
            raise ValidationError('El enlace debe ser un enlace válido de YouTube.')

    def obtener_link_incrustado(self):
        """
        Convierte el enlace de YouTube al formato de incrustación (embed).
        """
        match = re.search(r'(?:v=|youtu\.be/|embed/)([a-zA-Z0-9_-]{11})', self.link)
        if match:
            video_id = match.group(1)
            return f"https://www.youtube.com/embed/{video_id}"
        return None
