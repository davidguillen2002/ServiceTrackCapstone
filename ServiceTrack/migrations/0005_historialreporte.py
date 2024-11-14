# Generated by Django 5.1.1 on 2024-11-14 01:01

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ServiceTrack', '0004_retousuario_reto_completado_por'),
    ]

    operations = [
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
    ]