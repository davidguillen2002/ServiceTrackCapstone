# Generated by Django 5.1.1 on 2024-11-15 05:53

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
            name='Medalla',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('descripcion', models.TextField()),
                ('icono', models.ImageField(blank=True, null=True, upload_to='medallas/')),
                ('puntos_necesarios', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='Reto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('descripcion', models.TextField()),
                ('puntos_otorgados', models.IntegerField()),
                ('requisito', models.IntegerField(help_text='Ejemplo: cantidad de servicios completados o puntos a alcanzar')),
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
                ('calificacion', models.IntegerField(blank=True, null=True)),
                ('comentario_cliente', models.TextField(blank=True, null=True)),
                ('costo', models.DecimalField(decimal_places=2, max_digits=10)),
                ('equipo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ServiceTrack.equipo')),
            ],
        ),
        migrations.CreateModel(
            name='Enlace',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enlace', models.TextField()),
                ('descripcion', models.TextField()),
                ('servicio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ServiceTrack.servicio')),
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
                ('puntos', models.IntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('is_staff', models.BooleanField(default=False)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('medallas', models.ManyToManyField(blank=True, related_name='usuarios', to='ServiceTrack.medalla')),
                ('rol', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ServiceTrack.rol')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='servicio',
            name='tecnico',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tecnico_servicios', to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='RetoUsuario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_completado', models.DateTimeField(blank=True, null=True)),
                ('cumplido', models.BooleanField(default=False)),
                ('reto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ServiceTrack.reto')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
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
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ObservacionIncidente',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descripcion', models.TextField()),
                ('tipo_observacion', models.CharField(max_length=100)),
                ('comentarios', models.TextField(blank=True, null=True)),
                ('estado', models.CharField(max_length=50)),
                ('fecha_reportada', models.DateField()),
                ('fecha_fin', models.DateField(blank=True, null=True)),
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
                ('rol_destinatario', models.CharField(choices=[('administrador', 'Administrador'), ('tecnico', 'Técnico'), ('cliente', 'Cliente')], max_length=20)),
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
            model_name='equipo',
            name='cliente',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
