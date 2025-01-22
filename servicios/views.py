from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Avg, F, Q, FloatField, ExpressionWrapper, Count
from django.db.models.functions import Coalesce
from django.contrib.auth.decorators import user_passes_test, login_required
from ServiceTrack.models import Guia, Categoria, Servicio, Usuario, Notificacion, Equipo, ChatMessage, Capacitacion, ObservacionIncidente
from seguimiento.forms import ServicioEstadoForm
from .ai_utils import get_similar_guides, get_similar_guides_with_context
from django.http import JsonResponse
from django.template.loader import render_to_string
from .forms import ServicioForm, RepuestoForm, ConfirmarEntregaForm, CapacitacionForm, ClienteForm, IncidenteForm, EquipoForm
from django.contrib import messages
from django.core.paginator import Paginator
from openai import OpenAI, RateLimitError
from django.conf import settings
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
import markdown2
from django.db import transaction
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.hashers import make_password

client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Función para verificar si el usuario es técnico
def is_tecnico(user):
    return user.rol.nombre == "tecnico"

# Función para verificar si el usuario es administrador
def is_admin(user):
    return user.rol.nombre == "administrador"

# Crear Cliente (Solo Técnicos)
@login_required
@user_passes_test(is_tecnico)
def crear_cliente(request):
    if request.method == "POST":
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save(commit=False)
            cliente.rol = Usuario.objects.get(nombre="cliente")  # Asigna el rol cliente
            cliente.password = make_password(form.cleaned_data['password'])  # Hashea la contraseña
            cliente.tecnico_asignado = request.user  # Asigna el cliente al técnico autenticado
            cliente.save()
            messages.success(request, "Cliente creado exitosamente.")
            return redirect('listar_clientes_tecnico')
        else:
            messages.error(request, "Por favor, corrige los errores del formulario.")
    else:
        form = ClienteForm()
    return render(request, "servicios/crear_cliente.html", {"form": form})

# Listar Clientes Asignados (Solo Técnicos)
@login_required
@user_passes_test(is_tecnico)
def listar_clientes_tecnico(request):
    """
    Lista de clientes cuyos equipos están asociados al técnico autenticado.
    """
    equipos_atendidos = Equipo.objects.filter(servicio__tecnico=request.user).distinct()
    clientes = Usuario.objects.filter(
        rol__nombre="cliente",
        equipo__in=equipos_atendidos  # Clientes que poseen equipos atendidos por el técnico
    ).distinct().order_by('nombre')

    # Paginación: Mostrar 5 clientes por página
    paginator = Paginator(clientes, 5)
    page_number = request.GET.get('page')
    clientes_paginados = paginator.get_page(page_number)

    return render(request, "servicios/listar_clientes_tecnico.html", {"clientes": clientes_paginados})

@login_required
@user_passes_test(is_tecnico)
def detalle_cliente(request, cliente_id):
    """
    Muestra los detalles de un cliente específico cuyos equipos están asociados al técnico autenticado.
    """
    cliente = get_object_or_404(
        Usuario,
        id=cliente_id,
        rol__nombre="cliente"
    )

    # Filtrar equipos atendidos por el técnico y pertenecientes al cliente
    equipos_atendidos = Equipo.objects.filter(
        cliente=cliente,
        servicio__tecnico=request.user  # Validar que el técnico autenticado ha atendido estos equipos
    ).distinct()

    if not equipos_atendidos.exists():
        messages.error(request, "No tiene acceso a este cliente.")
        return redirect('listar_clientes_tecnico')

    return render(request, 'servicios/detalle_cliente.html', {
        'cliente': cliente,
        'equipos': equipos_atendidos,
    })

@login_required
@user_passes_test(is_tecnico)
def obtener_cliente_por_equipo(request):
    """
    Devuelve el nombre del cliente asociado a un equipo seleccionado.
    """
    equipo_id = request.GET.get('equipo_id')
    try:
        equipo = Equipo.objects.get(id=equipo_id)
        cliente_nombre = equipo.cliente.nombre
        return JsonResponse({'cliente': cliente_nombre}, status=200)
    except Equipo.DoesNotExist:
        return JsonResponse({'error': 'Equipo no encontrado'}, status=404)

@login_required
@user_passes_test(is_tecnico)
def actualizar_estado_servicio(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id, tecnico=request.user)

    if request.method == "POST":
        estado_anterior = servicio.estado
        form = ServicioEstadoForm(request.POST, instance=servicio)
        if form.is_valid():
            with transaction.atomic():
                servicio = form.save()

                # Crear notificación para el cliente
                Notificacion.crear_notificacion(
                    usuario=servicio.equipo.cliente,
                    tipo="actualizacion_servicio",
                    mensaje=(
                        f"El estado de su servicio para el equipo {servicio.equipo.marca} "
                        f"{servicio.equipo.modelo} ha cambiado de '{estado_anterior}' a '{servicio.estado}'."
                    )
                )

            messages.success(request, "Estado del servicio actualizado y cliente notificado.")
            return redirect("detalle_servicio", servicio_id=servicio.id)
        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
    else:
        form = ServicioEstadoForm(instance=servicio)

    return render(request, "servicios/actualizar_estado_servicio.html", {
        "form": form,
        "servicio": servicio,
    })


@login_required
@user_passes_test(is_tecnico)
def notificar_incidente(request, incidente_id):
    """
    Notifica a los clientes sobre incidentes reportados en sus servicios.
    """
    incidente = get_object_or_404(ObservacionIncidente, id=incidente_id)

    # Crear la notificación
    Notificacion.crear_notificacion(
        usuario=incidente.servicio.equipo.cliente,
        tipo="nueva_observacion",
        mensaje=(
            f"Se ha registrado un nuevo incidente en su servicio para el equipo "
            f"{incidente.servicio.equipo.marca} {incidente.servicio.equipo.modelo}: {incidente.descripcion}."
        )
    )

    messages.success(request, "Incidente notificado exitosamente al cliente.")
    return redirect("listar_incidentes", servicio_id=incidente.servicio.id)

# Crear Servicio
@login_required
@user_passes_test(is_tecnico)
def crear_servicio(request):
    """
    Vista para que un técnico registre un nuevo servicio para equipos asignados.
    """
    equipos_disponibles = Equipo.objects.filter(servicio__tecnico=request.user).distinct()

    if request.method == "POST":
        form = ServicioForm(request.POST, equipos_disponibles=equipos_disponibles)
        if form.is_valid():
            servicio = form.save(commit=False)
            servicio.tecnico = request.user  # Asignar el técnico autenticado

            # Validación para generar el código de entrega y notificación solo si el estado es "completado"
            if servicio.estado.lower() == "completado":
                servicio.generar_codigo_entrega()  # Generar código único para el servicio

                # Notificar al cliente
                Notificacion.crear_notificacion(
                    usuario=servicio.equipo.cliente,
                    tipo="codigo_entrega",
                    mensaje=f"Se ha creado un nuevo servicio para el equipo {servicio.equipo.marca}. "
                            f"Su código de entrega es: {servicio.codigo_entrega}."
                )
                messages.success(request, "El servicio completado ha sido creado y el cliente ha sido notificado.")
            else:
                servicio.codigo_entrega = None  # No generar código de entrega si no está completado
                estado_actual = servicio.get_estado_display()
                messages.warning(request,
                                 f"El servicio ha sido creado en estado '{estado_actual}', por lo que no se generó un código de entrega.")

            servicio.save()  # Guardar el servicio en la base de datos
            return redirect('tecnico_services_list')
        else:
            messages.error(request, "Por favor, corrige los errores del formulario.")
    else:
        form = ServicioForm(equipos_disponibles=equipos_disponibles)

    return render(request, "servicios/crear_servicio.html", {"form": form})

# CRUD de Incidentes
@login_required
@user_passes_test(is_tecnico)
def listar_incidentes(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id, tecnico=request.user)
    incidentes = ObservacionIncidente.objects.filter(servicio=servicio)

    return render(request, "servicios/listar_incidentes.html", {
        "servicio": servicio,
        "incidentes": incidentes
    })

@login_required
@user_passes_test(lambda u: u.rol.nombre == "tecnico")
def crear_incidente(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id, tecnico=request.user)
    if servicio.estado != "completado":
        if request.method == "POST":
            form = IncidenteForm(request.POST)
            if form.is_valid():
                incidente = form.save(commit=False)
                incidente.servicio = servicio
                incidente.autor = request.user
                incidente.save()

                # Notificación para el cliente
                Notificacion.crear_notificacion(
                    usuario=servicio.equipo.cliente,
                    tipo="nueva_observacion",
                    mensaje=(
                        f"Se ha registrado un nuevo incidente en su servicio para el equipo "
                        f"{servicio.equipo.marca} {servicio.equipo.modelo}: {incidente.descripcion}."
                    )
                )

                messages.success(request, "Incidente reportado exitosamente y cliente notificado.")
                return redirect('listar_incidentes', servicio_id=servicio.id)
            else:
                messages.error(request, "Por favor, corrige los errores del formulario.")
        else:
            form = IncidenteForm()
    else:
        messages.error(request, "No se pueden reportar incidentes para servicios completados.")
        return redirect('tecnico_services_list')

    return render(request, "servicios/crear_incidente.html", {
        "servicio": servicio,
        "form": form
    })

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

                # Notificación al cliente sobre la confirmación
                Notificacion.crear_notificacion(
                    usuario=servicio.equipo.cliente,
                    tipo="entrega_confirmada",
                    mensaje=f"El técnico ha confirmado la entrega de su equipo {servicio.equipo.marca} {servicio.equipo.modelo}."
                )

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
    """
    Vista para que un administrador registre un nuevo servicio.
    """
    equipos_disponibles = Equipo.objects.filter(cliente__isnull=False)  # Solo equipos con cliente asociado

    if request.method == "POST":
        servicio_form = ServicioForm(request.POST, equipos_disponibles=equipos_disponibles)
        if servicio_form.is_valid():
            servicio = servicio_form.save(commit=False)

            # Validación para generar el código de entrega y notificar solo si el estado es "completado"
            if servicio.estado.lower() == "completado":
                servicio.generar_codigo_entrega()  # Generar código único para el servicio

                # Notificar al cliente
                Notificacion.crear_notificacion(
                    usuario=servicio.equipo.cliente,
                    tipo="codigo_entrega",
                    mensaje=f"Se ha registrado un servicio para su equipo {servicio.equipo.marca} {servicio.equipo.modelo}. "
                            f"Su código de entrega es: {servicio.codigo_entrega}."
                )
                messages.success(request, "El servicio completado ha sido registrado y el cliente notificado.")
            else:
                servicio.codigo_entrega = None
                estado_actual = servicio.get_estado_display()
                messages.warning(request, f"El servicio ha sido registrado en estado '{estado_actual}', por lo que no se generó un código de entrega.")

            servicio.save()  # Guardar el servicio en la base de datos
            return redirect('lista_servicios')
        else:
            messages.error(request, "Por favor, corrige los errores del formulario.")
    else:
        servicio_form = ServicioForm(equipos_disponibles=equipos_disponibles)

    return render(request, "servicios/registrar_servicio.html", {
        "servicio_form": servicio_form,
    })


@login_required
@user_passes_test(is_admin)
def lista_servicios(request):
    """
    Vista para listar servicios con búsqueda y filtros, con soporte para paginación y solicitudes AJAX.
    """
    query = request.GET.get('q', '')
    filtro = request.GET.get('filtro', 'numero')  # Por defecto, filtrar por N# de Servicio

    # Filtrar los servicios basados en los parámetros de búsqueda y filtros
    servicios = Servicio.objects.all()
    if query:
        if filtro == "numero" and query.isdigit():
            servicios = servicios.filter(id=query)
        else:
            servicios = servicios.filter(
                Q(equipo__marca__icontains=query) |
                Q(equipo__modelo__icontains=query) |
                Q(tecnico__nombre__icontains=query) |
                Q(equipo__cliente__nombre__icontains=query)
            )
    elif filtro and filtro != "numero":
        servicios = servicios.filter(estado__iexact=filtro)
    else:
        servicios = Servicio.objects.all()

    # Asegurarse de que los resultados estén ordenados por ID
    servicios = servicios.order_by('-id')

    # Obtener los estados únicos sin modificar los valores reales
    estados = Servicio.objects.values_list('estado', flat=True).distinct()

    # Crear un mapeo para mostrar un formato amigable
    estados_mapeados = {estado: estado.replace('_', ' ').capitalize() for estado in estados}

    # Configurar la paginación
    paginator = Paginator(servicios, 5)
    page_number = request.GET.get('page', 1)
    servicios_paginados = paginator.get_page(page_number)

    # Manejar solicitudes AJAX para actualizar la lista de servicios
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('servicios/servicio_list_partial.html', {'servicios': servicios_paginados})
        return JsonResponse({'html': html})

    # Renderizar la página completa para solicitudes normales
    return render(request, "servicios/lista_servicios.html", {
        "servicios": servicios_paginados,
        "estados": estados_mapeados,  # Pasar el mapeo de estados a la plantilla
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
    """Vista para mostrar todos los servicios asociados a un técnico con paginación."""
    services = Servicio.objects.filter(tecnico=request.user).order_by('-fecha_inicio')

    # Paginación: Mostrar 5 servicios por página
    paginator = Paginator(services, 5)  # Cambia el número para ajustar los elementos por página
    page_number = request.GET.get('page')
    paginated_services = paginator.get_page(page_number)

    return render(request, 'servicios/tecnico_services_list.html', {'services': paginated_services})

@login_required
@user_passes_test(lambda u: u.rol.nombre in ["tecnico", "administrador"])
def chat(request):
    """Vista del chatbot personalizado para cada técnico."""
    # Filtrar historial de chat para el usuario autenticado
    chat_history = ChatMessage.objects.filter(user=request.user).order_by('created_at')
    response_text = None

    if request.method == "POST":
        user_message = request.POST.get('message', '')

        try:
            # Generar respuesta del bot
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                store=True,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )
            # Respuesta original en Markdown
            raw_response = completion.choices[0].message.content
            # Convertir Markdown a HTML
            response_text = markdown2.markdown(raw_response, extras=["fenced-code-blocks", "tables", "strike", "footnotes"])

        except RateLimitError:
            response_text = "Créditos insuficientes, contacte a administración."

        # Guardar mensajes en el historial con Markdown y HTML
        if response_text != "Créditos insuficientes, contacte a administración.":
            ChatMessage.objects.create(
                user=request.user,
                user_message=user_message,
                bot_response=response_text,
                raw_response=raw_response
            )

        return JsonResponse({"response": response_text})

    return render(request, 'servicios/chat.html', {"chat_history": chat_history})

# BASE DE CONOCIMIENTO
@login_required
@user_passes_test(lambda u: u.rol.nombre in ["tecnico", "administrador"])
def base_conocimiento(request):
    query = request.GET.get('q', '')
    categoria_filtro = request.GET.get('categoria', '')
    tipo_servicio_filtro = request.GET.get('tipo_servicio', '')
    marca_filtro = request.GET.get('marca', '')

    # Filtrar las guías
    guias = Guia.objects.all()
    if query:
        guias = guias.filter(Q(titulo__icontains=query) | Q(descripcion__icontains=query))
    if categoria_filtro:
        guias = guias.filter(categoria__nombre=categoria_filtro)
    if tipo_servicio_filtro:
        guias = guias.filter(tipo_servicio__icontains=tipo_servicio_filtro)
    if marca_filtro:
        guias = guias.filter(equipo_marca__icontains=marca_filtro)

    # Configurar la paginación
    paginator = Paginator(guias, 10)
    page_number = request.GET.get('page', 1)
    guias_paginadas = paginator.get_page(page_number)

    # Responder con el HTML parcial si es una solicitud AJAX
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('servicios/guia_list.html', {'guias': guias_paginadas})
        return JsonResponse({'html': html})

    # Enviar todos los filtros al contexto
    return render(request, 'servicios/base_conocimiento.html', {
        'guias': guias_paginadas,
        'categorias': Categoria.objects.all(),
        'tipos_servicio': Guia.objects.values_list('tipo_servicio', flat=True).distinct(),
        'marcas': Guia.objects.values_list('equipo_marca', flat=True).distinct(),
        'query': query,
        'categoria_filtro': categoria_filtro,
        'tipo_servicio_filtro': tipo_servicio_filtro,
        'marca_filtro': marca_filtro,
        'current_page': int(page_number),  # Página actual
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


# Vista para obtener guías recomendadas basadas en un servicio específico
@login_required
@user_passes_test(is_tecnico)
def register_service(request, service_id):
    """
    Vista para obtener guías recomendadas basadas en el servicio actual del técnico.
    Incluye recomendaciones contextuales según el historial del técnico.
    """
    current_service = get_object_or_404(Servicio, id=service_id, tecnico=request.user)

    # Obtener guías similares con contexto (servicio actual y técnico)
    similar_guides = get_similar_guides_with_context(current_service, request.user)

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
    Muestra los servicios relacionados con los equipos del cliente autenticado con paginación.
    """
    if request.user.rol.nombre != "cliente":
        return redirect("home")  # Redirige si no es cliente

    # Filtra los servicios relacionados con el cliente
    servicios = Servicio.objects.filter(equipo__cliente=request.user).order_by('-fecha_inicio')

    # Configura la paginación (5 servicios por página)
    paginator = Paginator(servicios, 5)
    page_number = request.GET.get('page')  # Obtiene el número de página desde la URL
    servicios_paginados = paginator.get_page(page_number)  # Obtiene los servicios correspondientes a la página

    # Renderiza el template con los servicios paginados
    return render(request, "servicios/lista_servicios_cliente.html", {
        "servicios": servicios_paginados,  # Pasa los servicios paginados al template
    })


# Enviar código al técnico (el cliente proporciona el código)
@login_required
def enviar_codigo_tecnico(request, servicio_id):
    """
    Vista para que el cliente confirme el código de entrega al técnico.
    """
    servicio = get_object_or_404(Servicio, id=servicio_id, equipo__cliente=request.user)

    if request.method == "POST":
        codigo_ingresado = request.POST.get('codigo_entrega')
        if codigo_ingresado == servicio.codigo_entrega:
            # Enviar notificación al técnico
            Notificacion.crear_notificacion(
                usuario=servicio.tecnico,
                tipo="codigo_entrega",
                mensaje=(
                    f"El cliente ha confirmado el código de entrega para el servicio del equipo "
                    f"{servicio.equipo.marca} {servicio.equipo.modelo}.\n"
                    f"**Código de Entrega:** {servicio.codigo_entrega}"
                )
            )
            messages.success(request, "El código ha sido confirmado exitosamente y enviado al técnico.")
            return redirect('lista_servicios_cliente')
        else:
            messages.error(request, "El código ingresado no es válido. Verifica nuevamente.")

    return render(request, 'servicios/enviar_codigo_tecnico.html', {
        'servicio': servicio
    })

# Listar capacitaciones (Disponible para técnicos y administradores)
def capacitacion_index(request):
    """
    Vista para mostrar las capacitaciones.
    """
    capacitaciones = Capacitacion.objects.all()
    for capacitacion in capacitaciones:
        capacitacion.embed_link = capacitacion.obtener_link_incrustado()
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


@login_required
@user_passes_test(is_tecnico)
def guide_preview(request, guide_id):
    """
    Endpoint para obtener detalles de una guía específica.
    """
    try:
        guia = get_object_or_404(Guia, id=guide_id)

        # Validar si el enlace del manual es una URL válida
        manual_url = guia.manual if isinstance(guia.manual, str) else None
        video_url = guia.video if isinstance(guia.video, str) else None

        data = {
            "titulo": guia.titulo,
            "descripcion": guia.descripcion,
            "manual_url": manual_url,
            "video_url": video_url,
        }
        return JsonResponse(data, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

@login_required
@user_passes_test(is_tecnico)
def agregar_repuesto(request, servicio_id):
    """
    Permite a un técnico agregar repuestos a un servicio que no haya sido completado.
    """
    servicio = get_object_or_404(Servicio, id=servicio_id, tecnico=request.user)

    # Verificar que el servicio no esté completado
    if servicio.estado == "completado":
        messages.error(request, "No se pueden agregar repuestos a servicios completados.")
        return redirect('detalle_servicio', servicio_id=servicio.id)

    # Procesar el formulario
    if request.method == "POST":
        form = RepuestoForm(request.POST)
        if form.is_valid():
            repuesto = form.save(commit=False)
            repuesto.servicio = servicio
            repuesto.save()

            messages.success(request, f"Repuesto '{repuesto.nombre}' agregado exitosamente al servicio.")
            return redirect('detalle_servicio', servicio_id=servicio.id)
        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
    else:
        form = RepuestoForm()

    return render(request, 'servicios/agregar_repuesto.html', {
        'servicio': servicio,
        'form': form,
    })

@login_required
@user_passes_test(lambda u: u.rol.nombre in ["administrador", "tecnico"])
def api_equipo_cliente(request):
    """
    API para obtener el cliente asociado a un equipo seleccionado.
    """
    equipo_id = request.GET.get('equipo_id')
    if not equipo_id:
        return JsonResponse({'error': 'No se proporcionó un ID de equipo.'}, status=400)

    try:
        equipo = Equipo.objects.get(id=equipo_id)
        if not equipo.cliente:
            return JsonResponse({'error': 'El equipo no tiene un cliente asociado.'}, status=404)

        cliente = equipo.cliente
        if not cliente.nombre:
            return JsonResponse({'error': 'El cliente asociado no tiene un nombre válido.'}, status=500)

        return JsonResponse({'cliente': cliente.nombre}, status=200)
    except Equipo.DoesNotExist:
        return JsonResponse({'error': 'Equipo no encontrado.'}, status=404)

# Listar equipos (Administradores pueden ver todo, técnicos ven equipos relacionados con ellos)
@login_required
@user_passes_test(lambda u: u.rol.nombre in ["administrador", "tecnico"])
def lista_equipos(request):
    # Determinar si es administrador o técnico para filtrar equipos
    if request.user.rol.nombre == "administrador":
        equipos = Equipo.objects.all()
    else:
        equipos = Equipo.objects.filter(servicio__tecnico=request.user).distinct()

    # Obtener los parámetros de búsqueda
    cedula_cliente = request.GET.get('cedula', '')
    marca = request.GET.get('marca', '')
    tipo_equipo = request.GET.get('tipo_equipo', '')

    # Aplicar filtros si existen
    if cedula_cliente:
        equipos = equipos.filter(cliente__cedula__icontains=cedula_cliente)
    if marca:
        equipos = equipos.filter(marca__icontains=marca)
    if tipo_equipo:
        equipos = equipos.filter(tipo_equipo__icontains=tipo_equipo)

    # Ordenar por marca y configurar la paginación
    equipos = equipos.order_by('marca')
    paginator = Paginator(equipos, 5)  # Mostrar 5 equipos por página
    page_number = request.GET.get('page')
    equipos_paginados = paginator.get_page(page_number)

    return render(request, "servicios/lista_equipos.html", {
        "equipos": equipos_paginados,
        "cedula_cliente": cedula_cliente,
        "marca": marca,
        "tipo_equipo": tipo_equipo
    })


# Crear equipo (Solo administradores)
@login_required
@user_passes_test(is_admin)
def crear_equipo(request):
    if request.method == "POST":
        form = EquipoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Equipo registrado exitosamente.")
            return redirect("lista_equipos")
        else:
            messages.error(request, "Por favor corrige los errores en el formulario.")
    else:
        form = EquipoForm()
    return render(request, "servicios/crear_equipo.html", {"form": form})


# Editar equipo (Solo administradores)
@login_required
@user_passes_test(is_admin)
def editar_equipo(request, equipo_id):
    equipo = get_object_or_404(Equipo, id=equipo_id)
    if request.method == "POST":
        form = EquipoForm(request.POST, instance=equipo)
        if form.is_valid():
            form.save()
            messages.success(request, "Equipo actualizado exitosamente.")
            return redirect("lista_equipos")
        else:
            messages.error(request, "Por favor corrige los errores en el formulario.")
    else:
        form = EquipoForm(instance=equipo)
    return render(request, "servicios/editar_equipo.html", {"form": form})


# Eliminar equipo (Solo administradores)
@login_required
@user_passes_test(is_admin)
def eliminar_equipo(request, equipo_id):
    equipo = get_object_or_404(Equipo, id=equipo_id)
    if request.method == "POST":
        equipo.delete()
        messages.success(request, "Equipo eliminado exitosamente.")
        return redirect("lista_equipos")
    return render(request, "servicios/eliminar_equipo.html", {"equipo": equipo})
