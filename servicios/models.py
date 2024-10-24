from django.db import models

class Rol(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    def __str__(self):
        return self.nombre

class Usuario(models.Model):
    nombre = models.CharField(max_length=100)
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=255)
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE)
    cedula = models.CharField(max_length=20, unique=True)
    correo = models.EmailField(max_length=100)
    celular = models.CharField(max_length=20)
    puntos = models.IntegerField(default=0)
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
    tecnico = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    calificacion = models.IntegerField(null=True, blank=True)
    comentario_cliente = models.TextField(null=True, blank=True)
    costo = models.DecimalField(max_digits=10, decimal_places=2)
    def __str__(self):
        return f"Servicio #{self.id} - {self.equipo}"

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.nombre

class Guia(models.Model):
    titulo = models.CharField(max_length=255)
    descripcion = models.TextField()
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    manual = models.FileField(upload_to='manuales/', null=True, blank=True)
    video = models.URLField(max_length=500, null=True, blank=True)
    tipo_servicio = models.CharField(max_length=100, null=True)
    equipo_marca = models.CharField(max_length=100, null=True)
    equipo_modelo = models.CharField(max_length=100, null=True)
    puntuacion = models.FloatField(default=0)
    def __str__(self):
        return self.titulo