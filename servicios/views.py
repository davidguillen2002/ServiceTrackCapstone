from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Avg, F, Q, FloatField, ExpressionWrapper, Count
from django.db.models.functions import Coalesce
from django.contrib.auth.decorators import user_passes_test, login_required
from ServiceTrack.models import Guia, Categoria, Servicio, Usuario, Notificacion, Equipo, ChatMessage, Capacitacion
from seguimiento.forms import ServicioEstadoForm
from .ai_utils import get_similar_guides
from django.http import JsonResponse
from django.template.loader import render_to_string
from .forms import ServicioForm, RepuestoForm, ConfirmarEntregaForm, CapacitacionForm
from django.contrib import messages
from django.core.paginator import Paginator
from openai import OpenAI, RateLimitError
from django.conf import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Función para verificar si el usuario es técnico
def is_tecnico(user):
    return user.rol.nombre == "tecnico"

# Función para verificar si el usuario es administrador
def is_admin(user):
    return user.rol.nombre == "administrador"

# Confirmar Entrega (El técnico valida el código proporcionado por el cliente)
@login_required
@user_passes_test(is_tecnico)
def confirmar_entrega(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id, tecnico=request.user)

    if request.method == "POST":
        form = ConfirmarEntregaForm(request.POST)
        if form.is_valid():
            codigo = form.cleaned_data['codigo_entrega']
            if servicio.codigo_entrega == codigo:
                servicio.entrega_confirmada = True
                servicio.save()
                messages.success(request, "La entrega ha sido confirmada exitosamente.")
                return redirect('tecnico_services_list')
            else:
                messages.error(request, "El código ingresado es incorrecto.")
    else:
        form = ConfirmarEntregaForm()

    return render(request, 'servicios/confirmar_entrega.html', {'form': form, 'servicio': servicio})

# Registrar Servicio (Envío del código al cliente)
@login_required
@user_passes_test(is_admin)
def registrar_servicio(request):
    if request.method == "POST":
        servicio_form = ServicioForm(request.POST)
        repuesto_form = RepuestoForm(request.POST)
        if servicio_form.is_valid() and repuesto_form.is_valid():
            servicio = servicio_form.save(commit=False)
            servicio.generar_codigo_entrega()  # Genera un código único
            servicio.save()

            # Enviar notificación al cliente
            Notificacion.crear_notificacion(
                usuario=servicio.equipo.cliente,
                tipo="codigo_entrega",
                mensaje=f"Su código de entrega para el servicio del equipo {servicio.equipo.marca} {servicio.equipo.modelo} es: {servicio.codigo_entrega}."
            )

            messages.success(request, "Servicio registrado y código enviado al cliente.")
            return redirect("lista_servicios")
    else:
        servicio_form = ServicioForm()
        repuesto_form = RepuestoForm()

    return render(request, "servicios/registrar_servicio.html", {
        "servicio_form": servicio_form,
        "repuesto_form": repuesto_form
    })

@login_required
@user_passes_test(is_admin)
def lista_servicios(request):
    # Recibir parámetros de búsqueda y filtros
    query = request.GET.get('q', '')
    estado_filtro = request.GET.get('estado', '')

    # Filtrar los servicios basados en los parámetros de búsqueda
    servicios = Servicio.objects.all()
    if query:
        servicios = servicios.filter(Q(equipo__modelo__icontains=query) | Q(tecnico__nombre__icontains=query))
    if estado_filtro:
        servicios = servicios.filter(estado=estado_filtro)

    # Obtener los estados únicos para el filtro
    estados = Servicio.objects.values_list('estado', flat=True).distinct().order_by('estado')

    # Paginación: Mostrar 5 servicios por página
    paginator = Paginator(servicios, 5)
    page_number = request.GET.get('page', 1)
    servicios_paginados = paginator.get_page(page_number)

    # Si es una solicitud AJAX, devolver solo el contenido filtrado
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('servicios/servicio_list.html', {'servicios': servicios_paginados})
        return JsonResponse({'html': html})

    # En caso de una solicitud normal, renderizar la página completa
    return render(request, "servicios/lista_servicios.html", {
        "servicios": servicios_paginados,
        "estados": estados,
    })

@login_required
@user_passes_test(is_admin)
def actualizar_servicio(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id)
    if request.method == "POST":
        form = ServicioForm(request.POST, instance=servicio)
        if form.is_valid():
            form.save()

            # Notificación para el cliente si el servicio se completa
            if servicio.estado == "completado":
                Notificacion.crear_notificacion(
                    usuario=servicio.equipo.cliente,
                    tipo="servicio_completado",
                    mensaje=f"Su servicio para el equipo {servicio.equipo.marca} {servicio.equipo.modelo} ha sido completado."
                )

            # No se necesita enviar WebSocket directamente aquí
            return redirect("lista_servicios")
    else:
        form = ServicioForm(instance=servicio)
    return render(request, "servicios/actualizar_servicio.html", {"form": form, "servicio": servicio})

@login_required
@user_passes_test(is_admin)
def eliminar_servicio(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id)
    if request.method == "POST":
        servicio.delete()
        messages.success(request, "Servicio eliminado correctamente.")
        return redirect("lista_servicios")  # Redirige a la lista de servicios después de eliminar
    return render(request, "servicios/eliminar_servicio.html", {"servicio": servicio})

def historial_servicios(request, equipo_id):
    equipo = get_object_or_404(Equipo, id=equipo_id)
    servicios = Servicio.objects.filter(equipo=equipo).order_by('-fecha_inicio')

    return render(request, 'servicios/historial_servicios.html', {
        'equipo': equipo,
        'servicios': servicios
    })

@login_required
@user_passes_test(is_tecnico)
def tecnico_services_list(request):
    """Vista para mostrar todos los servicios asociados a un técnico."""
    services = Servicio.objects.filter(tecnico=request.user)
    return render(request, 'servicios/tecnico_services_list.html', {'services': services})

@login_required
@user_passes_test(is_tecnico)
def register_service(request, service_id):
    """Vista para obtener guías recomendadas para un servicio específico del técnico."""
    current_service = get_object_or_404(Servicio, id=service_id, tecnico=request.user)
    similar_guides = get_similar_guides(current_service)
    return render(request, 'servicios/similar_guides.html', {
        'current_service': current_service,
        'similar_guides': similar_guides,
    })

@login_required
@user_passes_test(lambda u: u.rol.nombre in ["tecnico", "administrador"])
def chat(request):
    chat_history = ChatMessage.objects.all().order_by('created_at')
    response_text = None

    if request.method == "POST":
        user_message = request.POST.get('message', '')

        try:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                store=True,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )
            response_text = completion.choices[0].message.content

        except RateLimitError:
            response_text = "Créditos insuficientes, contacte a administración."

        # Guardar en la base de datos solo si la respuesta es válida
        if response_text != "Créditos insuficientes, contacte a administración.":
            ChatMessage.objects.create(user_message=user_message, bot_response=response_text)

        return JsonResponse({"response": response_text})

    return render(request, 'servicios/chat.html', {"chat_history": chat_history})


# BASE DE CONOCIMIENTO
@login_required
@user_passes_test(lambda u: u.rol.nombre in ["tecnico", "administrador"])
def base_conocimiento(request):
    query = request.GET.get('q', '')
    categoria_filtro = request.GET.get('categoria', '')
    tipo_servicio_filtro = request.GET.get('tipo_servicio', '')

    guias = Guia.objects.all()
    if query:
        guias = guias.filter(Q(titulo__icontains=query) | Q(descripcion__icontains=query))
    if categoria_filtro:
        guias = guias.filter(categoria__nombre=categoria_filtro)
    if tipo_servicio_filtro:
        guias = guias.filter(tipo_servicio__icontains=tipo_servicio_filtro)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('servicios/guia_list.html', {'guias': guias})
        return JsonResponse({'html': html})

    categorias = Categoria.objects.all()
    tipos_servicio = Guia.objects.values_list('tipo_servicio', flat=True).distinct()

    return render(request, 'servicios/base_conocimiento.html', {
        'guias': guias,
        'categorias': categorias,
        'tipos_servicio': tipos_servicio,
        'query': query,
        'categoria_filtro': categoria_filtro,
        'tipo_servicio_filtro': tipo_servicio_filtro
    })

@login_required
@user_passes_test(is_admin)
def knowledge_dashboard(request):
    servicios_por_estado = (
        Servicio.objects.values('estado')  # Agrupar por estado
        .annotate(total=Count('id'))       # Contar servicios por estado
        .order_by('estado')                # Ordenar por estado
    )
    labels = [item['estado'] for item in servicios_por_estado]  # Etiquetas para el gráfico
    data = [item['total'] for item in servicios_por_estado]     # Datos para el gráfico

    total_servicios = Servicio.objects.count()
    calificacion_promedio = Servicio.objects.filter(calificacion__isnull=False).aggregate(Avg('calificacion'))['calificacion__avg']
    guias_mas_consultadas = Guia.objects.order_by('-puntuacion')[:5]
    tecnicos = Usuario.objects.filter(rol__nombre='tecnico')

    context = {
        'labels': labels,
        'data': data,
        'total_servicios': total_servicios,
        'calificacion_promedio': calificacion_promedio,
        'guias_mas_consultadas': guias_mas_consultadas,
        'tecnicos': tecnicos,
    }
    return render(request, 'servicios/knowledge_dashboard.html', context)

@login_required
@user_passes_test(lambda u: u.rol.nombre in ["tecnico", "administrador"])
def guia_detalle(request, guia_id):
    guia = get_object_or_404(Guia, id=guia_id)
    return render(request, 'servicios/guia_detalle.html', {'guia': guia})

@login_required
@user_passes_test(lambda u: u.rol.nombre in ["tecnico", "administrador"])
def register_service(request, service_id):
    current_service = get_object_or_404(Servicio, id=service_id)
    similar_guides = get_similar_guides(current_service)
    return render(request, 'servicios/similar_guides.html', {
        'current_service': current_service,
        'similar_guides': similar_guides,
    })

@login_required
def detalle_servicio(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id)
    repuestos = servicio.repuestos.all()  # Acceder a los repuestos relacionados
    return render(request, 'servicios/detalle_servicio.html', {
        'servicio': servicio,
        'repuestos': repuestos
    })

@login_required
@user_passes_test(lambda u: u.rol.nombre == "tecnico")
def actualizar_estado_equipo_tecnico(request, equipo_id):
    servicio = get_object_or_404(Servicio, equipo_id=equipo_id, tecnico=request.user)

    if not servicio.entrega_confirmada:
        messages.error(request, "No puede cambiar el estado hasta que la entrega sea confirmada.")
        return redirect('detalle_servicio', servicio_id=servicio.id)

    if request.method == 'POST':
        form = ServicioEstadoForm(request.POST, instance=servicio)
        if form.is_valid():
            form.save()
            messages.success(request, "El estado del servicio ha sido actualizado.")
            return redirect('lista_equipos_tecnico')
    else:
        form = ServicioEstadoForm(instance=servicio)

    return render(request, 'servicios/actualizar_estado_equipo_tecnico.html', {'form': form, 'servicio': servicio})

@login_required
def lista_servicios_cliente(request):
    """
    Muestra los servicios relacionados con los equipos del cliente autenticado.
    """
    if request.user.rol.nombre != "cliente":
        return redirect("home")  # Redirige si no es cliente

    servicios = Servicio.objects.filter(equipo__cliente=request.user).order_by('-fecha_inicio')

    return render(request, "servicios/lista_servicios_cliente.html", {
        "servicios": servicios,
    })

@login_required
def enviar_codigo_tecnico(request, servicio_id):
    """
    Vista para que el cliente envíe el código de entrega al técnico.
    """
    servicio = get_object_or_404(Servicio, id=servicio_id, equipo__cliente=request.user)

    if request.method == "POST":
        codigo_ingresado = request.POST.get('codigo_entrega')
        if codigo_ingresado == servicio.codigo_entrega:
            # Enviar notificación al técnico
            Notificacion.crear_notificacion(
                usuario=servicio.tecnico,
                tipo="codigo_entrega",
                mensaje=f"El cliente ha confirmado el código de entrega para el servicio del equipo {servicio.equipo.marca} {servicio.equipo.modelo}: {codigo_ingresado}."
            )
            messages.success(request, "Código enviado exitosamente al técnico.")
            return redirect('lista_servicios_cliente')
        else:
            messages.error(request, "El código ingresado es incorrecto.")

    return render(request, 'servicios/enviar_codigo_tecnico.html', {
        'servicio': servicio
    })

# Listar capacitaciones (Disponible para técnicos y administradores)
@login_required
def capacitacion_index(request):
    capacitaciones = Capacitacion.objects.all()
    return render(request, 'servicios/capacitacion_index.html', {'capacitaciones': capacitaciones})

# Crear capacitación (Solo para administradores)
@login_required
@user_passes_test(is_admin)
def capacitacion_create(request):
    if request.method == "POST":
        form = CapacitacionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('capacitacion_index')
    else:
        form = CapacitacionForm()
    return render(request, 'servicios/capacitacion_form.html', {'form': form})

# Editar capacitación (Solo para administradores)
@login_required
@user_passes_test(is_admin)
def capacitacion_edit(request, capacitacion_id):
    capacitacion = get_object_or_404(Capacitacion, id=capacitacion_id)
    if request.method == "POST":
        form = CapacitacionForm(request.POST, instance=capacitacion)
        if form.is_valid():
            form.save()
            return redirect('capacitacion_index')
    else:
        form = CapacitacionForm(instance=capacitacion)
    return render(request, 'servicios/capacitacion_form.html', {'form': form})

# Eliminar capacitación (Solo para administradores)
@login_required
@user_passes_test(is_admin)
def capacitacion_delete(request, capacitacion_id):
    capacitacion = get_object_or_404(Capacitacion, id=capacitacion_id)
    if request.method == "POST":
        capacitacion.delete()
        return redirect('capacitacion_index')
    return render(request, 'servicios/capacitacion_confirm_delete.html', {'capacitacion': capacitacion})