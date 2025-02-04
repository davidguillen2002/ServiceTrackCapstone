# Generated by Django 5.1.1 on 2025-01-23 21:57

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Capacitacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=255)),
                ('descripcion_corta', models.TextField(max_length=500)),
                ('link', models.URLField()),
            ],
        ),
        migrations.CreateModel(
            name='Categoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Equipo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('marca', models.CharField(max_length=50)),
                ('modelo', models.CharField(max_length=50)),
                ('anio', models.IntegerField()),
                ('tipo_equipo', models.CharField(max_length=50)),
                ('observaciones', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Rol',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=50, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Temporada',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(help_text='Ejemplo: Temporada 2025-I', max_length=50)),
                ('fecha_inicio', models.DateField()),
                ('fecha_fin', models.DateField()),
                ('activa', models.BooleanField(default=True, help_text='Indica si la temporada está activa')),
            ],
        ),
        migrations.CreateModel(
            name='TipoObservacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Guia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=255)),
                ('descripcion', models.TextField()),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('manual', models.TextField(blank=True, null=True)),
                ('video', models.TextField(blank=True, null=True)),
                ('tipo_servicio', models.CharField(blank=True, max_length=100, null=True)),
                ('equipo_marca', models.CharField(blank=True, max_length=100, null=True)),
                ('equipo_modelo', models.CharField(blank=True, max_length=100, null=True)),
                ('puntuacion', models.FloatField(default=0)),
                ('categoria', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ServiceTrack.categoria')),
            ],
        ),
        migrations.CreateModel(
            name='Servicio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_inicio', models.DateField()),
                ('fecha_fin', models.DateField(blank=True, null=True)),
                ('estado', models.CharField(choices=[('pendiente', 'Pendiente'), ('en_progreso', 'En Progreso'), ('completado', 'Completado')], default='pendiente', max_length=20)),
                ('calificacion', models.DecimalField(blank=True, decimal_places=1, help_text='Calificación de 1 a 5, admite decimales', max_digits=3, null=True)),
                ('comentario_cliente', models.TextField(blank=True, null=True)),
                ('diagnostico_inicial', models.TextField(blank=True, null=True)),
                ('costo', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('codigo_entrega', models.CharField(blank=True, max_length=6, null=True)),
                ('entrega_confirmada', models.BooleanField(default=False)),
                ('equipo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ServiceTrack.equipo')),
            ],
            options={
                'ordering': ['-fecha_inicio'],
            },
        ),
        migrations.CreateModel(
            name='Repuesto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('descripcion', models.TextField(blank=True, null=True)),
                ('costo', models.DecimalField(decimal_places=2, max_digits=10)),
                ('proveedor', models.CharField(blank=True, max_length=100, null=True)),
                ('cantidad', models.PositiveIntegerField(default=1)),
                ('servicio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='repuestos', to='ServiceTrack.servicio')),
            ],
        ),
        migrations.CreateModel(
            name='Enlace',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enlace', models.TextField()),
                ('descripcion', models.TextField()),
                ('servicio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='enlaces', to='ServiceTrack.servicio')),
            ],
        ),
        migrations.CreateModel(
            name='Reto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('descripcion', models.TextField()),
                ('puntos_otorgados', models.IntegerField()),
                ('nivel', models.IntegerField(default=1, help_text='Nivel asociado al reto. Define el nivel necesario para desbloquear este reto.')),
                ('criterio', models.CharField(choices=[('puntos', 'Alcanzar cierta cantidad de puntos'), ('servicios', 'Completar una cantidad de servicios'), ('calificaciones', 'Lograr una calificación promedio mínima')], help_text='Define cómo se valida el cumplimiento del reto.', max_length=50)),
                ('valor_objetivo', models.IntegerField(help_text='Ejemplo: 500 puntos, 10 servicios, o calificación promedio de 4')),
                ('temporada', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='retos', to='ServiceTrack.temporada')),
            ],
        ),
        migrations.CreateModel(
            name='Recompensa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descripcion', models.TextField(help_text='Descripción detallada de la recompensa.')),
                ('valor', models.DecimalField(decimal_places=2, help_text='Valor monetario o simbólico asociado a la recompensa.', max_digits=10)),
                ('puntos_necesarios', models.IntegerField(help_text='Cantidad de puntos requeridos para redimir esta recompensa.')),
                ('tipo', models.CharField(help_text='Tipo de recompensa: bono, herramienta o trofeo.', max_length=50)),
                ('reto', models.OneToOneField(blank=True, help_text='Reto asociado directamente a esta recompensa (opcional).', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recompensa', to='ServiceTrack.reto')),
                ('temporada', models.ForeignKey(help_text='Temporada a la que pertenece esta recompensa.', on_delete=django.db.models.deletion.CASCADE, related_name='recompensas', to='ServiceTrack.temporada')),
            ],
            options={
                'verbose_name': 'Recompensa',
                'verbose_name_plural': 'Recompensas',
                'ordering': ['temporada', 'tipo'],
            },
        ),
        migrations.CreateModel(
            name='Medalla',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('descripcion', models.TextField()),
                ('icono', models.ImageField(blank=True, null=True, upload_to='medallas/')),
                ('puntos_necesarios', models.IntegerField()),
                ('nivel_requerido', models.IntegerField(default=1, help_text='Nivel mínimo requerido para obtener esta medalla.')),
                ('retos_asociados', models.ManyToManyField(blank=True, related_name='medallas_asociadas', to='ServiceTrack.reto')),
                ('temporada', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='medallas', to='ServiceTrack.temporada')),
            ],
        ),
        migrations.CreateModel(
            name='EstadisticaTemporada',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('puntos_totales', models.IntegerField(default=0)),
                ('nivel_alcanzado', models.IntegerField(default=0)),
                ('retos_completados', models.IntegerField(default=0)),
                ('temporada', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ServiceTrack.temporada')),
            ],
        ),
        migrations.CreateModel(
            name='Usuario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('nombre', models.CharField(max_length=100)),
                ('username', models.CharField(max_length=100, unique=True)),
                ('password', models.CharField(max_length=255)),
                ('cedula', models.CharField(max_length=20, unique=True)),
                ('correo', models.EmailField(max_length=100)),
                ('celular', models.CharField(max_length=20)),
                ('puntos', models.IntegerField(default=0, help_text='Puntos acumulados por el usuario.')),
                ('experiencia', models.IntegerField(default=0, help_text='Experiencia actual del usuario.')),
                ('nivel', models.IntegerField(default=1, help_text='Nivel actual del usuario.')),
                ('servicios_completados', models.IntegerField(default=0, help_text='Total de servicios completados.')),
                ('calificacion_promedio', models.FloatField(default=0.0, help_text='Calificación promedio acumulada.')),
                ('servicios_solicitados', models.IntegerField(default=0, help_text='Número total de servicios solicitados por el cliente.')),
                ('is_active', models.BooleanField(default=True)),
                ('is_staff', models.BooleanField(default=False)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('medallas', models.ManyToManyField(blank=True, related_name='tecnicos', to='ServiceTrack.medalla')),
                ('rol', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ServiceTrack.rol')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'Usuario',
                'verbose_name_plural': 'Usuarios',
                'ordering': ['-nivel', '-puntos'],
            },
        ),
        migrations.AddField(
            model_name='temporada',
            name='usuarios_participantes',
            field=models.ManyToManyField(related_name='temporadas', through='ServiceTrack.EstadisticaTemporada', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='servicio',
            name='tecnico',
            field=models.ForeignKey(limit_choices_to={'rol__nombre': 'tecnico'}, on_delete=django.db.models.deletion.CASCADE, related_name='tecnico_servicios', to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='RetoUsuario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cumplido', models.BooleanField(default=False)),
                ('progreso', models.FloatField(default=0, help_text='Progreso actual del usuario en el reto (en %).')),
                ('cantidad_actual', models.FloatField(default=0, help_text='Progreso absoluto en el reto.')),
                ('fecha_completado', models.DateTimeField(blank=True, null=True)),
                ('reto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='retos_asignados', to='ServiceTrack.reto')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='retos_usuario', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='reto',
            name='completado_por',
            field=models.ManyToManyField(related_name='retos_completados', through='ServiceTrack.RetoUsuario', to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='RegistroPuntos',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('puntos_obtenidos', models.IntegerField()),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('descripcion', models.TextField()),
                ('es_conversion_experiencia', models.BooleanField(default=False)),
                ('servicio', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='ServiceTrack.servicio')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='RecompensaUsuario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('redimido', models.BooleanField(default=False, help_text='Indica si el usuario ya redimió esta recompensa.')),
                ('fecha_asignacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_redencion', models.DateTimeField(blank=True, null=True)),
                ('recompensa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='usuarios_asignados', to='ServiceTrack.recompensa')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recompensas_usuario', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Recompensa de Usuario',
                'verbose_name_plural': 'Recompensas de Usuarios',
            },
        ),
        migrations.AddField(
            model_name='recompensa',
            name='usuarios_redimidos',
            field=models.ManyToManyField(blank=True, help_text='Usuarios que han redimido esta recompensa.', related_name='recompensas_redimidas', through='ServiceTrack.RecompensaUsuario', to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='ObservacionIncidente',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descripcion', models.TextField()),
                ('comentarios', models.TextField(blank=True, null=True)),
                ('estado', models.CharField(max_length=50)),
                ('fecha_reportada', models.DateField()),
                ('fecha_fin', models.DateField(blank=True, null=True)),
                ('servicio', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='observaciones', to='ServiceTrack.servicio')),
                ('tipo_observacion', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='observaciones', to='ServiceTrack.tipoobservacion')),
                ('autor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Notificacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('nuevo_servicio', 'Nuevo Servicio Asignado'), ('servicio_completado', 'Servicio Completado'), ('reto_asignado', 'Nuevo Reto Asignado'), ('actualizacion_reporte', 'Actualización de Reporte'), ('nueva_observacion', 'Nueva Observación en un Incidente'), ('nuevo_equipo', 'Nuevo Equipo Registrado')], max_length=30)),
                ('mensaje', models.TextField()),
                ('fecha_creacion', models.DateTimeField(default=django.utils.timezone.now)),
                ('leido', models.BooleanField(default=False)),
                ('extra_data', models.JSONField(blank=True, null=True)),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notificaciones', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-fecha_creacion'],
            },
        ),
        migrations.CreateModel(
            name='HistorialReporte',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_generacion', models.DateTimeField(auto_now_add=True)),
                ('tipo_reporte', models.CharField(choices=[('PDF', 'PDF'), ('Excel', 'Excel')], max_length=10)),
                ('archivo', models.FileField(blank=True, null=True, upload_to='reportes/')),
                ('generado_por', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='estadisticatemporada',
            name='usuario',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='equipo',
            name='cliente',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_message', models.TextField(help_text='Mensaje enviado por el usuario.')),
                ('bot_response', models.TextField(help_text='Respuesta generada por el bot en HTML.')),
                ('raw_response', models.TextField(blank=True, help_text='Respuesta original generada por el bot en formato Markdown.', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(help_text='Usuario asociado al mensaje.', on_delete=django.db.models.deletion.CASCADE, related_name='chat_messages', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name='retousuario',
            constraint=models.UniqueConstraint(fields=('usuario', 'reto'), name='unique_usuario_reto'),
        ),
        migrations.AlterUniqueTogether(
            name='recompensausuario',
            unique_together={('usuario', 'recompensa')},
        ),
        migrations.AddConstraint(
            model_name='recompensa',
            constraint=models.UniqueConstraint(fields=('reto',), name='unique_recompensa_por_reto'),
        ),
    ]
