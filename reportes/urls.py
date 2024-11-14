# reportes/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('panel/', views.panel_reportes, name='panel_reportes'),
    path('reporte/pdf/', views.generar_reporte_pdf, name='reporte_pdf'),
    path('reporte/excel/', views.generar_reporte_excel, name='reporte_excel'),
    path('historial/', views.historial_reportes, name='historial_reportes'),
]