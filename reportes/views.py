# reportes/views.py
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.files.base import ContentFile
from reportlab.pdfgen import canvas
from ServiceTrack.models import Servicio, HistorialReporte
from datetime import datetime
import pandas as pd
import io

def is_admin(user):
    return user.is_superuser or (user.rol.nombre == "administrador")

def is_tecnico(user):
    return user.rol.nombre == "tecnico"

@login_required
def panel_reportes(request):
    return render(request, 'reportes/reporte_dashboard.html')

@login_required
@user_passes_test(lambda u: is_admin(u) or is_tecnico(u))
def generar_reporte_pdf(request):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 800, "Reporte de Servicios Completados")
    p.drawString(100, 780, f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # Diferenciar datos según rol
    servicios = Servicio.objects.filter(estado='completado')
    y = 750
    for servicio in servicios:
        texto = f"Servicio {servicio.id}: Técnico {servicio.tecnico.nombre}, Calificación {servicio.calificacion}" if is_admin(request.user) else f"Servicio {servicio.id}: Calificación {servicio.calificacion}"
        p.drawString(100, y, texto)
        y -= 20
        if y < 100:
            p.showPage()
            y = 750

    p.save()
    buffer.seek(0)
    file_content = buffer.getvalue()
    buffer.close()

    archivo_reporte = ContentFile(file_content, f"reporte_servicios_{datetime.now().strftime('%Y%m%d')}.pdf")
    reporte = HistorialReporte.objects.create(tipo_reporte='PDF', generado_por=request.user)
    reporte.archivo.save(archivo_reporte.name, archivo_reporte)
    return HttpResponse(file_content, content_type='application/pdf')

@login_required
@user_passes_test(lambda u: is_admin(u) or is_tecnico(u))
def generar_reporte_excel(request):
    servicios = Servicio.objects.filter(estado='completado')
    data = servicios.values('id', 'tecnico__nombre', 'fecha_inicio', 'fecha_fin', 'calificacion', 'costo') if is_admin(request.user) else servicios.values('id', 'fecha_inicio', 'fecha_fin', 'calificacion')
    df = pd.DataFrame(list(data))

    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = f'attachment; filename="reporte_servicios_{datetime.now().strftime("%Y%m%d")}.xlsx"'
    with io.BytesIO() as buffer:
        df.to_excel(buffer, index=False)
        file_content = buffer.getvalue()

    archivo_reporte = ContentFile(file_content, f"reporte_servicios_{datetime.now().strftime('%Y%m%d')}.xlsx")
    reporte = HistorialReporte.objects.create(tipo_reporte='Excel', generado_por=request.user)
    reporte.archivo.save(archivo_reporte.name, archivo_reporte)
    return HttpResponse(file_content, content_type='application/vnd.ms-excel')

@login_required
def historial_reportes(request):
    reportes = HistorialReporte.objects.filter(generado_por=request.user) if is_tecnico(request.user) else HistorialReporte.objects.all()
    return render(request, 'reportes/historial_reportes.html', {'reportes': reportes})