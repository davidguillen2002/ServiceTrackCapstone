from django.urls import path
from . import views

urlpatterns = [
    path('panel/', views.panel_reportes, name='panel_reportes'),
    path('panel/tecnicos/', views.panel_reportes_tecnicos, name='panel_reportes_tecnicos'),  # Nueva ruta
    path('reporte/tecnico/pdf/', views.generar_reporte_pdf_tecnico, name='reporte_pdf_tecnico'),
    path('reporte/tecnico/excel/', views.generar_reporte_excel_tecnico, name='reporte_excel_tecnico'),
    path('reporte/pdf/', views.generar_reporte_pdf, name='reporte_pdf'),
    path('reporte/excel/', views.generar_reporte_excel, name='reporte_excel'),
    path('historial/', views.historial_reportes, name='historial_reportes'),
    path('incidentes/', views.analizar_incidentes, name='analizar_incidentes'),
    path('notificaciones/', views.notificaciones_kpis, name='notificaciones_kpis'),
    path('repuestos/', views.analizar_repuestos, name='analizar_repuestos'),
    path('filtrar_repuestos/', views.filtrar_repuestos, name='filtrar_repuestos'),
]