from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.files.base import ContentFile
from reportlab.pdfgen import canvas
from ServiceTrack.models import Servicio, HistorialReporte, Notificacion, Usuario, Repuesto
from datetime import datetime
import pandas as pd
import io
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Sum, F, ExpressionWrapper, DurationField, FloatField, Q
from django.template.loader import render_to_string

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
    Vista para analizar los incidentes registrados con métricas clave y gráficos.
    """
    # Calcular incidentes por diagnóstico
    incidentes = Servicio.objects.filter(estado='pendiente').values('diagnostico_inicial').annotate(
        total=Count('id')
    ).order_by('-total')

    # Calcular métricas clave
    total_incidentes = sum([incidente['total'] for incidente in incidentes])  # Sumar manualmente los valores de 'total'
    diagnostico_mas_comun = incidentes[0]['diagnostico_inicial'] if incidentes else "N/A"
    incidentes_criticos = len([incidente for incidente in incidentes if incidente['total'] >= 10])  # Incidentes críticos >= 10

    # Preparar datos para gráficas
    diagnosticos = [incidente['diagnostico_inicial'] for incidente in incidentes]
    totales = [incidente['total'] for incidente in incidentes]

    context = {
        'incidentes': incidentes,
        'diagnosticos': diagnosticos,
        'totales': totales,
        'total_incidentes': total_incidentes,
        'diagnostico_mas_comun': diagnostico_mas_comun,
        'incidentes_criticos': incidentes_criticos,
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
    Vista para analizar el rendimiento de repuestos con un filtro dinámico.
    """
    query = request.GET.get('q', '')  # Obtener el parámetro de búsqueda desde el request
    repuestos = Repuesto.objects.filter(
        Q(nombre__icontains=query)  # Filtrar repuestos por nombre que contenga el texto ingresado
    ).values('nombre').annotate(
        total_uso=Count('id'),
        total_fallas=Count(
            'servicio__id',
            filter=Q(servicio__estado='fallido')
        ),
        tasa_fallas=ExpressionWrapper(
            F('total_fallas') * 100.0 / F('total_uso'),
            output_field=FloatField()
        ),
        costo_promedio=Avg('costo')
    ).order_by('-total_uso')

    total_repuestos = sum(repuesto['total_uso'] for repuesto in repuestos)
    repuesto_mas_usado = max(repuestos, key=lambda x: x['total_uso'], default=None)
    repuesto_mas_fallas = max(repuestos, key=lambda x: x['tasa_fallas'], default=None)

    # Preparar datos para gráficas
    nombres_repuestos = [repuesto['nombre'] for repuesto in repuestos]
    usos_repuestos = [repuesto['total_uso'] for repuesto in repuestos]

    context = {
        'repuestos': repuestos,
        'total_repuestos': total_repuestos,
        'repuesto_mas_usado': repuesto_mas_usado or {'nombre': 'N/A', 'total_uso': 0},
        'repuesto_mas_fallas': repuesto_mas_fallas or {'nombre': 'N/A', 'tasa_fallas': 0},
        'nombres_repuestos': nombres_repuestos,
        'usos_repuestos': usos_repuestos,
        'query': query  # Pasar el valor del filtro actual al contexto
    }
    return render(request, 'reportes/analisis_repuestos.html', context)



@login_required
@user_passes_test(lambda u: u.rol.nombre == "tecnico")
def panel_reportes_tecnicos(request):
    usuario = request.user
    servicios = Servicio.objects.filter(tecnico=usuario).order_by('-fecha_inicio')

    # Paginación
    paginator = Paginator(servicios, 10)  # 10 servicios por página
    page_number = request.GET.get('page')
    servicios_paginados = paginator.get_page(page_number)

    # KPIs
    total_servicios = servicios.filter(estado='completado').count()
    promedio_calificacion = servicios.filter(estado='completado').aggregate(Avg('calificacion'))['calificacion__avg'] or 0
    tiempo_promedio_resolucion = servicios.filter(estado='completado').annotate(
        dias_resolucion=ExpressionWrapper(
            F('fecha_fin') - F('fecha_inicio'),
            output_field=DurationField()
        )
    ).aggregate(Avg('dias_resolucion'))['dias_resolucion__avg']

    context = {
        'total_servicios': total_servicios,
        'promedio_calificacion': round(promedio_calificacion, 2),
        'tiempo_promedio_resolucion': round(tiempo_promedio_resolucion.days, 1) if tiempo_promedio_resolucion else "N/A",
        'servicios': servicios_paginados,
    }

    return render(request, 'reportes/reporte_tecnicos.html', context)

@login_required
@user_passes_test(lambda u: u.rol.nombre == "tecnico")
def generar_reporte_pdf_tecnico(request):
    """
    Generar reporte en PDF para técnicos con información limitada a sus servicios.
    """
    usuario = request.user
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 800, "Reporte de Servicios Completados")
    p.drawString(100, 780, f"Técnico: {usuario.nombre}")
    p.drawString(100, 760, f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    servicios = Servicio.objects.filter(tecnico=usuario, estado='completado')

    # KPIs del técnico
    total_servicios = servicios.count()
    promedio_calificacion = servicios.aggregate(Avg('calificacion'))['calificacion__avg'] or 0

    y = 720
    p.drawString(100, y, f"Total de Servicios Completados: {total_servicios}")
    y -= 20
    p.drawString(100, y, f"Promedio de Calificación: {round(promedio_calificacion, 2)}")
    y -= 40

    for servicio in servicios:
        texto = f"Servicio {servicio.id} - Equipo: {servicio.equipo}, Calificación: {servicio.calificacion}"
        p.drawString(100, y, texto)
        y -= 20
        if y < 100:
            p.showPage()
            y = 750

    p.save()
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')


@login_required
@user_passes_test(lambda u: u.rol.nombre == "tecnico")
def generar_reporte_excel_tecnico(request):
    """
    Generar reporte en Excel para técnicos con información limitada a sus servicios.
    """
    usuario = request.user
    servicios = Servicio.objects.filter(tecnico=usuario, estado='completado')
    data = servicios.values('id', 'equipo__marca', 'fecha_inicio', 'fecha_fin', 'calificacion')

    df = pd.DataFrame(list(data))
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = f'attachment; filename="reporte_servicios_tecnico_{datetime.now().strftime("%Y%m%d")}.xlsx"'
    with io.BytesIO() as buffer:
        df.to_excel(buffer, index=False)
        file_content = buffer.getvalue()

    return HttpResponse(file_content, content_type='application/vnd.ms-excel')

from django.db.models import Count, Avg, Q, F, ExpressionWrapper, FloatField

@login_required
@user_passes_test(is_admin)
def filtrar_repuestos(request):
    query = request.GET.get('q', '')  # Obtener el texto de búsqueda
    repuestos = Repuesto.objects.filter(
        nombre__icontains=query  # Filtrar por nombre
    ).values('nombre').annotate(  # Agrupar por 'nombre'
        total_uso=Sum('cantidad'),  # Sumar la cantidad total de repuestos
        tasa_fallas=ExpressionWrapper(
            Count('servicio__id', filter=Q(servicio__estado='fallido')) * 100.0 / Count('id'),
            output_field=FloatField()
        ),
        costo_promedio=Avg('costo')  # Calcular el costo promedio
    ).order_by('-total_uso')  # Ordenar por el total de uso

    return JsonResponse({
        'tabla': render_to_string('partials/tabla_repuestos.html', {'repuestos': repuestos}),
    })
