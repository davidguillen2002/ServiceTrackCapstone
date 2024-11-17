from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.files.base import ContentFile
from reportlab.pdfgen import canvas
from ServiceTrack.models import Servicio, HistorialReporte, Notificacion, Usuario, Repuesto
from datetime import datetime
import pandas as pd
import io
from django.db.models import Avg, Count, Sum, F

# Helper para verificar roles
def is_admin(user):
    return user.is_superuser or (user.rol.nombre == "administrador")

# Panel de Reportes
@login_required
@user_passes_test(is_admin)
def panel_reportes(request):
    """
    Vista principal del panel de reportes.
    """
    return render(request, 'reportes/reporte_dashboard.html')

# Generar Reporte PDF
@login_required
@user_passes_test(is_admin)
def generar_reporte_pdf(request):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 800, "Reporte de Servicios Completados y KPIs")
    p.drawString(100, 780, f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    servicios = Servicio.objects.filter(estado='completado')

    # KPIs
    promedio_calificacion = servicios.aggregate(Avg('calificacion'))['calificacion__avg'] or 0
    total_servicios = servicios.count()
    costo_total = servicios.aggregate(Sum('costo'))['costo__sum'] or 0

    y = 750
    p.drawString(100, y, f"Promedio de Calificación: {round(promedio_calificacion, 2)}")
    y -= 20
    p.drawString(100, y, f"Total de Servicios Completados: {total_servicios}")
    y -= 20
    p.drawString(100, y, f"Costo Total de Servicios: ${round(costo_total, 2)}")
    y -= 40

    for servicio in servicios:
        texto = f"Servicio {servicio.id}: Técnico {servicio.tecnico.nombre}, Calificación {servicio.calificacion}"
        p.drawString(100, y, texto)
        y -= 20
        if y < 100:
            p.showPage()
            y = 750

    p.save()
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')

# Generar Reporte Excel
@login_required
@user_passes_test(is_admin)
def generar_reporte_excel(request):
    servicios = Servicio.objects.filter(estado='completado')
    data = servicios.values('id', 'tecnico__nombre', 'fecha_inicio', 'fecha_fin', 'calificacion', 'costo')

    # KPIs
    promedio_calificacion = servicios.aggregate(Avg('calificacion'))['calificacion__avg'] or 0
    total_servicios = servicios.count()
    costo_total = servicios.aggregate(Sum('costo'))['costo__sum'] or 0

    df = pd.DataFrame(list(data))
    df.loc[len(df.index)] = ["KPIs", "", "", "", promedio_calificacion, costo_total]

    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = f'attachment; filename="reporte_servicios_{datetime.now().strftime("%Y%m%d")}.xlsx"'
    with io.BytesIO() as buffer:
        df.to_excel(buffer, index=False)
        file_content = buffer.getvalue()

    return HttpResponse(file_content, content_type='application/vnd.ms-excel')

# Historial de Reportes
@login_required
@user_passes_test(is_admin)
def historial_reportes(request):
    """
    Vista para mostrar el historial de reportes generados.
    """
    reportes = HistorialReporte.objects.all().order_by('-fecha_generacion')
    return render(request, 'reportes/historial_reportes.html', {'reportes': reportes})

# Análisis de Incidentes
@login_required
@user_passes_test(is_admin)
def analizar_incidentes(request):
    """
    Vista para analizar los incidentes registrados con gráficos.
    """
    incidentes = Servicio.objects.filter(estado='pendiente').values('diagnostico_inicial').annotate(
        total=Count('id')
    ).order_by('-total')

    # Preparar datos para gráficas
    diagnosticos = [incidente['diagnostico_inicial'] for incidente in incidentes]
    totales = [incidente['total'] for incidente in incidentes]

    context = {
        'incidentes': incidentes,
        'diagnosticos': diagnosticos,
        'totales': totales
    }
    return render(request, 'reportes/analisis_incidentes.html', context)

def generar_alertas_incidentes():
    """
    Genera alertas si el recuento de incidentes para un diagnóstico supera un umbral.
    """
    umbral = 5  # Definir el umbral
    incidentes = Servicio.objects.filter(estado='pendiente').values('diagnostico_inicial').annotate(
        total=Count('id')
    )

    for incidente in incidentes:
        if incidente['total'] > umbral:
            Notificacion.crear_notificacion(
                usuario=None,  # Asignar a un administrador
                tipo="incidente_critico",
                mensaje=f"Alta recurrencia detectada para el diagnóstico '{incidente['diagnostico_inicial']}' con {incidente['total']} incidentes."
            )

# Notificaciones de KPIs
@login_required
@user_passes_test(is_admin)
def notificaciones_kpis(request):
    """
    Vista para mostrar las notificaciones relacionadas con KPIs críticos.
    """
    notificaciones = Notificacion.objects.filter(tipo__in=["kpi_bajo", "incidente_critico"]).order_by('-fecha_creacion')
    return render(request, 'reportes/notificaciones_kpis.html', {'notificaciones': notificaciones})

@login_required
@user_passes_test(is_admin)
def analizar_repuestos(request):
    """
    Vista para analizar el rendimiento de repuestos.
    """
    repuestos = Repuesto.objects.values('nombre').annotate(
        total_uso=Count('id'),
        tasa_fallas=Count('servicio__id', filter=F('servicio__estado') == 'fallido') * 100 / Count('servicio__id')
    ).order_by('-total_uso')

    return render(request, 'reportes/analisis_repuestos.html', {'repuestos': repuestos})
