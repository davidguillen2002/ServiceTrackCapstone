import json
import pandas as pd
from django.db.models import Count, Min, Sum
from ServiceTrack.models import Usuario, Servicio, Reto, RetoUsuario, RegistroPuntos, Medalla, ObservacionIncidente, \
    Temporada, EstadisticaTemporada, Recompensa, Notificacion
from django.utils.timezone import now
from .notifications import notificar_tecnico, notificar_tecnico_con_animacion
import joblib
import os
from django.db import models
from django.core.exceptions import ValidationError
import json
import pandas as pd
from django.db.models import Sum, Avg
from ServiceTrack.models import (
    RegistroPuntos, RetoUsuario, Temporada, ObservacionIncidente, RecompensaUsuario
)
from django.utils.timezone import now
import joblib
import os
from django.db import transaction

def generar_recomendaciones_con_ia(tecnico):
    """
    Genera recomendaciones personalizadas para un técnico utilizando un modelo de aprendizaje automático.
    Incluye análisis basado en temporada actual y progreso en retos.
    """
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    ruta_modelo = os.path.join(BASE_DIR, "modelo_recomendaciones.pkl")
    ruta_mapping = os.path.join(BASE_DIR, "label_mapping.json")

    try:
        # Cargar el modelo y el mapeo de etiquetas
        modelo = joblib.load(ruta_modelo)
        with open(ruta_mapping, "r") as f:
            label_mapping = json.load(f)
    except Exception as e:
        print(f"Error al cargar el modelo o el mapeo: {e}")
        return ["Error al generar recomendaciones con IA."]

    # Calcular puntos totales del técnico
    puntos_totales = RegistroPuntos.objects.filter(usuario=tecnico).aggregate(
        total=Sum('puntos_obtenidos')
    )['total'] or 0

    # Crear el DataFrame con las columnas en el mismo orden que en el entrenamiento
    columnas_modelo = [
        "nivel", "experiencia", "puntos", "calificacion_promedio",
        "servicios_completados", "incidentes_reportados", "tiempo_promedio_horas", "puntos_totales"
    ]

    datos_tecnico = pd.DataFrame([{
        "nivel": tecnico.nivel,
        "experiencia": tecnico.experiencia,
        "puntos": tecnico.puntos,
        "calificacion_promedio": tecnico.calificacion_promedio or 0,
        "servicios_completados": tecnico.tecnico_servicios.filter(estado="completado").count(),
        "incidentes_reportados": ObservacionIncidente.objects.filter(servicio__tecnico=tecnico).count(),
        "tiempo_promedio_horas": tecnico.calcular_promedio_tiempo_servicio() or 0,
        "puntos_totales": puntos_totales,
    }], columns=columnas_modelo)

    recomendaciones = []
    temporada_actual = Temporada.obtener_temporada_actual()

    if not temporada_actual:
        recomendaciones.append("No hay una temporada activa. Completa tus objetivos en el próximo periodo.")
        return recomendaciones

    try:
        # Generar predicción
        prediccion = modelo.predict(datos_tecnico)
        etiqueta_prediccion = int(prediccion[0])  # Convertir la predicción a entero

        # Determinar retos cumplidos y pendientes del nivel actual y temporada activa
        retos_cumplidos = RetoUsuario.objects.filter(
            usuario=tecnico, cumplido=True, reto__nivel=tecnico.nivel, reto__temporada=temporada_actual
        ).count()
        retos_disponibles = RetoUsuario.objects.filter(
            usuario=tecnico, cumplido=False, reto__nivel=tecnico.nivel, reto__temporada=temporada_actual
        ).count()

        # Generar texto según retos cumplidos y disponibles
        if retos_cumplidos >= 2:
            texto_recomendacion = "¡Estás avanzando rápidamente! Considera asumir retos más desafiantes."
        elif retos_cumplidos == 1:
            texto_recomendacion = "Estás en camino, completa otro reto para desbloquear beneficios adicionales."
        else:
            texto_recomendacion = "Aún tienes retos pendientes. ¡Empieza con uno simple para acumular experiencia rápidamente!"
        recomendaciones.append(texto_recomendacion)

    except ValueError as ve:
        print(f"Error al mapear la etiqueta de predicción: {ve}")
        recomendaciones.append("Revisión manual requerida.")
    except Exception as e:
        print(f"Error al generar predicciones: {e}")
        return ["Error al generar recomendaciones con IA."]

    # Recomendaciones personalizadas basadas en desempeño
    if tecnico.calificacion_promedio and tecnico.calificacion_promedio < 4:
        recomendaciones.append("Trabaja en mejorar tus calificaciones para alcanzar un promedio de 4 o más.")
    elif tecnico.calificacion_promedio and tecnico.calificacion_promedio >= 4:
        recomendaciones.append("¡Excelente! Mantén tus calificaciones altas para destacar aún más.")

    if tecnico.puntos < 500:
        recomendaciones.append("Acumula más puntos completando servicios con alta calidad.")
    else:
        recomendaciones.append("¡Impresionante! Estás acumulando puntos rápidamente. Considera apoyar a otros técnicos.")

    # Recomendaciones basadas en retos pendientes del nivel actual y temporada activa
    retos_pendientes = RetoUsuario.objects.filter(
        usuario=tecnico,
        cumplido=False,
        reto__nivel=tecnico.nivel,
        reto__temporada=temporada_actual
    ).select_related('reto')

    for reto_usuario in retos_pendientes:
        progreso = reto_usuario.progreso or 0  # Manejar progreso nulo
        if progreso < 50:
            recomendaciones.append(f"Enfócate en el reto '{reto_usuario.reto.nombre}', aún puedes avanzar significativamente.")
        else:
            recomendaciones.append(f"Estás cerca de completar el reto '{reto_usuario.reto.nombre}'. ¡No te detengas ahora!")

    return recomendaciones

def otorgar_puntos_por_servicio(usuario):
    """
    Otorga puntos por servicios completados no procesados. Ajusta los puntos otorgados
    para evitar un avance excesivo en niveles y considera el rendimiento del técnico.
    """
    servicios_completados = usuario.tecnico_servicios.filter(estado='completado').exclude(
        id__in=RegistroPuntos.objects.filter(usuario=usuario).values_list('servicio_id', flat=True)
    )

    puntos_totales = 0
    registros = []

    for servicio in servicios_completados:
        # Calcular puntos otorgados por el servicio
        puntos_base = 10  # Puntos iniciales por completar un servicio
        puntos_extra = max(0, (servicio.calificacion or 0) - 3) * 5  # Puntos extra por calificación mayor a 3
        puntos_servicio = puntos_base + puntos_extra

        # Validar que los puntos no excedan lo necesario para completar el nivel actual
        experiencia_requerida = usuario.calcular_experiencia_nivel_siguiente()
        if usuario.puntos + puntos_servicio > experiencia_requerida:
            puntos_servicio = experiencia_requerida - usuario.puntos

        puntos_totales += puntos_servicio

        # Registrar los puntos obtenidos
        registros.append(RegistroPuntos(
            usuario=usuario,
            servicio=servicio,
            puntos_obtenidos=puntos_servicio,
            descripcion=f"Servicio {servicio.id} completado"
        ))

    # Registrar los puntos y guardar cambios
    RegistroPuntos.objects.bulk_create(registros)
    usuario.puntos += puntos_totales
    usuario.save()

    return puntos_totales


from django.utils.timezone import now
from ServiceTrack.models import RegistroPuntos, RetoUsuario, Medalla
from gamificacion.notifications import notificar_tecnico, notificar_tecnico_con_animacion


from django.utils.timezone import now
from ServiceTrack.models import RegistroPuntos, RetoUsuario, Medalla, Recompensa
from gamificacion.notifications import notificar_tecnico, notificar_tecnico_con_animacion

def verificar_y_asignar_medallas_y_retos(usuario):
    """
    Verifica si el usuario cumple con los requisitos para medallas y sincroniza retos asociados,
    asegurándose de validar correctamente los criterios para medallas y retos.
    """
    medallas = Medalla.objects.all()
    animaciones = []  # Lista para acumular las animaciones que se enviarán al frontend

    for medalla in medallas:
        # Verificar si el usuario cumple con los requisitos de la medalla
        retos_cumplidos = all(
            RetoUsuario.objects.filter(usuario=usuario, reto=reto, cumplido=True).exists()
            for reto in medalla.retos_asociados.all()
        )
        if (
            retos_cumplidos
            and usuario.puntos >= medalla.puntos_necesarios
            and usuario.nivel >= medalla.nivel_requerido
            and not usuario.medallas.filter(id=medalla.id).exists()
        ):
            usuario.medallas.add(medalla)
            RegistroPuntos.objects.create(
                usuario=usuario,
                puntos_obtenidos=0,  # No otorgar puntos adicionales al asignar medallas
                descripcion=f"Medalla '{medalla.nombre}' otorgada"
            )

            # Crear notificación para el técnico con animación
            notificar_tecnico_con_animacion(
                usuario,
                f"¡Has ganado la medalla '{medalla.nombre}'! 🎉",
                tipo="success",
                animacion="bounceIn"
            )
            animaciones.append({
                "tipo": "success",
                "mensaje": f"¡Has ganado la medalla '{medalla.nombre}'! 🎉",
                "animacion": "bounceIn",
            })

            # Marcar retos asociados como cumplidos si corresponde
            for reto in medalla.retos_asociados.all():
                reto_usuario = RetoUsuario.objects.filter(usuario=usuario, reto=reto).first()
                if reto_usuario and not reto_usuario.cumplido:
                    reto_usuario.cumplido = True
                    reto_usuario.progreso = 100
                    reto_usuario.fecha_completado = now()
                    reto_usuario.save()

    # Verificar progreso de retos pendientes
    retos = RetoUsuario.objects.filter(usuario=usuario, cumplido=False)
    experiencia_total = 0  # Acumular la experiencia proporcional

    for reto_usuario in retos:
        reto_usuario.actualizar_progreso()
        reto_usuario.verificar_cumplimiento()
        experiencia_total += (reto_usuario.progreso / 100) * reto_usuario.reto.puntos_otorgados  # Progresión proporcional

        if reto_usuario.progreso >= 100 and not reto_usuario.cumplido:
            reto_usuario.cumplido = True
            reto_usuario.fecha_completado = now()
            reto_usuario.save()

            # Crear notificación para el técnico con animación
            notificar_tecnico_con_animacion(
                usuario,
                f"¡Has completado el reto '{reto_usuario.reto.nombre}'! 🏆",
                tipo="info",
                animacion="rubberBand"
            )
            animaciones.append({
                "tipo": "info",
                "mensaje": f"¡Has completado el reto '{reto_usuario.reto.nombre}'! 🏆",
                "animacion": "rubberBand",
            })

            # Otorgar puntos por el reto completado
            usuario.puntos += reto_usuario.reto.puntos_otorgados
            RegistroPuntos.objects.create(
                usuario=usuario,
                puntos_obtenidos=reto_usuario.reto.puntos_otorgados,
                descripcion=f"Reto completado: {reto_usuario.reto.nombre}"
            )

    # Verificar si el usuario tiene experiencia suficiente para subir de nivel
    experiencia_requerida = usuario.calcular_experiencia_nivel_siguiente()
    while usuario.experiencia >= experiencia_requerida and usuario.nivel < 5:
        exceso_experiencia = usuario.experiencia - experiencia_requerida

        # Incrementar nivel y reiniciar experiencia
        usuario.nivel += 1
        usuario.experiencia = exceso_experiencia

        # Asignar nuevos retos para el nivel actual
        usuario.asignar_retos_por_nivel()

        # Crear notificación para el técnico con animación
        notificar_tecnico_con_animacion(
            usuario,
            f"¡Felicidades {usuario.nombre}, has alcanzado el nivel {usuario.nivel}! 🎉",
            tipo="info",
            animacion="tada"
        )
        animaciones.append({
            "tipo": "info",
            "mensaje": f"¡Felicidades {usuario.nombre}, has alcanzado el nivel {usuario.nivel}! 🎉",
            "animacion": "tada",
        })

        experiencia_requerida = usuario.calcular_experiencia_nivel_siguiente()

    # Ajustar experiencia sobrante si se alcanza el nivel máximo
    if usuario.nivel >= 5:
        usuario.experiencia = 0

    usuario.save()
    return animaciones  # Devolver la lista de animaciones para el frontend


def generar_recomendaciones_para_tecnico(tecnico):
    """
    Genera recomendaciones personalizadas para un técnico basado en su desempeño.
    """
    recomendaciones = []

    # Calcular tiempos promedio
    promedio_tiempo = tecnico.calcular_promedio_tiempo_servicio()
    if promedio_tiempo:
        if promedio_tiempo > 7:
            recomendaciones.append("Reduce tu tiempo promedio de servicio para mejorar la eficiencia.")
        elif promedio_tiempo < 3:
            recomendaciones.append("¡Excelente! Mantén un tiempo de servicio eficiente.")
    else:
        recomendaciones.append("Aún no hay suficientes datos sobre tiempos de servicio.")

    # Revisar calificaciones bajas
    calificaciones_bajas = Servicio.objects.filter(tecnico=tecnico, calificacion__lt=3).count()
    if calificaciones_bajas > 5:
        recomendaciones.append(f"Revisa los {calificaciones_bajas} servicios con calificaciones bajas para buscar áreas de mejora.")
    elif calificaciones_bajas == 0:
        recomendaciones.append("¡Buen trabajo! No tienes servicios con calificaciones bajas.")

    # Patrones de incidentes
    incidentes = ObservacionIncidente.objects.filter(servicio__tecnico=tecnico).count()
    if incidentes > 3:
        recomendaciones.append("Analiza los incidentes frecuentes y toma medidas para prevenir futuros problemas.")
    elif incidentes == 0:
        recomendaciones.append("¡Bien hecho! No se han registrado incidentes en tus servicios.")

    # Verificar nivel de puntos
    if tecnico.puntos < 300:
        recomendaciones.append("Completa más servicios con altas calificaciones para aumentar tu puntaje.")
    elif tecnico.calificacion_promedio < 4:
        recomendaciones.append("Apunta a un promedio de calificación de 4 o más para desbloquear retos premium.")

    # Verificar retos pendientes
    retos_pendientes = RetoUsuario.objects.filter(usuario=tecnico, cumplido=False).count()
    if retos_pendientes > 0:
        recomendaciones.append(f"Tienes {retos_pendientes} retos pendientes. ¡No te olvides de completarlos!")
    else:
        recomendaciones.append("¡Excelente! Has completado todos tus retos actuales.")

    return recomendaciones

def asignar_retos_dinamicos(tecnico):
    """
    Asigna retos específicos al técnico según su nivel actual.
    """
    # Obtener los retos para el nivel actual del técnico
    retos_nivel = Reto.objects.filter(nivel=tecnico.nivel)
    print(f"Retos disponibles para nivel {tecnico.nivel}: {retos_nivel}")

    for reto in retos_nivel:
        # Crear una relación en RetoUsuario si no existe
        reto_usuario, created = RetoUsuario.objects.get_or_create(
            usuario=tecnico,
            reto=reto,
            defaults={'cumplido': False, 'progreso': 0}
        )
        if created:
            print(f"Reto asignado: {reto.nombre} al usuario {tecnico.nombre}")
        else:
            print(f"Reto ya existente: {reto.nombre} para usuario {tecnico.nombre}")

def otorgar_experiencia(self, cantidad):
    """
    Otorga experiencia al usuario, verifica si sube de nivel y ajusta retos asociados.
    """
    self.experiencia += cantidad
    while self.experiencia >= self.calcular_experiencia_nivel_siguiente() and self.nivel < 5:
        exceso = self.experiencia - self.calcular_experiencia_nivel_siguiente()
        self.nivel += 1
        self.experiencia = exceso

        # Crear notificación para el usuario
        Notificacion.crear_notificacion(
            usuario=self,
            tipo="nivel_cliente",
            mensaje=f"¡Felicidades {self.nombre}, has alcanzado el nivel {self.nivel}! 🎉"
        )

        # Asignar retos del nuevo nivel
        self.asignar_retos_por_nivel()

    self.save()


def limpiar_duplicados_retousuario():
    """
    Elimina registros duplicados en la tabla RetoUsuario, dejando solo el más antiguo.
    También asegura que solo queden retos asignados al nivel correcto.
    """
    duplicados = (
        RetoUsuario.objects.values('usuario', 'reto')
        .annotate(total=Count('id'), min_id=Min('id'))
        .filter(total__gt=1)
    )

    for duplicado in duplicados:
        RetoUsuario.objects.filter(
            usuario_id=duplicado['usuario'],
            reto_id=duplicado['reto']
        ).exclude(id=duplicado['min_id']).delete()

    # Eliminar retos asignados a usuarios en niveles incorrectos
    for usuario in Usuario.objects.filter(rol__nombre="tecnico"):
        RetoUsuario.objects.filter(usuario=usuario).exclude(reto__nivel=usuario.nivel).delete()

def finalizar_temporada():
    """
    Finaliza la temporada activa y configura la próxima temporada.
    """
    fecha_actual = now().date()
    temporada_actual = Temporada.obtener_temporada_actual()

    if not temporada_actual:
        print("No hay temporada activa para finalizar.")
        return

    # Registrar estadísticas de todos los usuarios
    usuarios = Usuario.objects.all()

    for usuario in usuarios:
        EstadisticaTemporada.objects.create(
            usuario=usuario,
            temporada=temporada_actual,
            puntos_totales=usuario.puntos,
            nivel_alcanzado=usuario.nivel,
            retos_completados=usuario.retos_usuario.filter(cumplido=True).count(),
        )

        # Reiniciar datos del usuario
        usuario.puntos = 0
        usuario.nivel = 1
        usuario.experiencia = 0
        usuario.medallas.clear()
        usuario.save()

    # Cerrar temporada actual
    temporada_actual.activa = False
    temporada_actual.save()

    # Activar la siguiente temporada
    siguiente_temporada = Temporada.objects.filter(fecha_inicio__gte=fecha_actual).first()
    if siguiente_temporada:
        siguiente_temporada.activa = True
        siguiente_temporada.save()
        print(f"Nueva temporada '{siguiente_temporada.nombre}' activada.")
    else:
        # Crear automáticamente temporadas para el próximo año
        Temporada.crear_temporadas_anuales()
        print("Se crearon nuevas temporadas para el siguiente año.")


# Función para sincronizar recompensas globales
def sincronizar_recompensas_globales(temporada_actual):
    """
    Sincroniza las recompensas globales por nivel para la temporada actual
    y las asocia a retos correspondientes en el mismo orden en que aparecen.
    """
    descripcion_recompensas = {
        1: [
            {"tipo": "Bono", "descripcion": "Bono de $100", "valor": 100, "puntos": 20},
            {"tipo": "Herramienta", "descripcion": "Kit básico de herramientas", "valor": 150, "puntos": 20},
            {"tipo": "Trofeo", "descripcion": "Trofeo: Técnico en Entrenamiento", "valor": 200, "puntos": 20},
        ],
        2: [
            {"tipo": "Bono", "descripcion": "Bono de $150", "valor": 150, "puntos": 40},
            {"tipo": "Herramienta", "descripcion": "Multímetro digital avanzado", "valor": 200, "puntos": 40},
            {"tipo": "Trofeo", "descripcion": "Trofeo: Técnico en Progreso", "valor": 300, "puntos": 40},
        ],
        3: [
            {"tipo": "Bono", "descripcion": "Bono de $200", "valor": 200, "puntos": 60},
            {"tipo": "Herramienta", "descripcion": "Juego profesional de herramientas", "valor": 300, "puntos": 60},
            {"tipo": "Trofeo", "descripcion": "Trofeo: Técnico Experto", "valor": 400, "puntos": 60},
        ],
        4: [
            {"tipo": "Bono", "descripcion": "Bono de $300", "valor": 300, "puntos": 80},
            {"tipo": "Herramienta", "descripcion": "Estación de soldadura avanzada", "valor": 400, "puntos": 80},
            {"tipo": "Trofeo", "descripcion": "Trofeo: Técnico Avanzado", "valor": 600, "puntos": 80},
        ],
        5: [
            {"tipo": "Bono", "descripcion": "Bono de $500", "valor": 500, "puntos": 100},
            {"tipo": "Herramienta", "descripcion": "Maletín premium especializado", "valor": 600, "puntos": 100},
            {"tipo": "Trofeo", "descripcion": "Trofeo: Maestro Técnico", "valor": 800, "puntos": 100},
        ],
    }

    print("[INFO] Sincronizando recompensas globales para la temporada actual.")

    for nivel, recompensas in descripcion_recompensas.items():
        # Obtener los retos de este nivel en el orden en que están en la base de datos
        retos_nivel = list(
            Reto.objects.filter(temporada=temporada_actual, nivel=nivel).order_by("id")
        )
        recompensa_index = 0

        for recompensa_data in recompensas:
            # Buscar o crear la recompensa
            recompensa, created = Recompensa.objects.get_or_create(
                temporada=temporada_actual,
                tipo=recompensa_data["tipo"],
                descripcion=recompensa_data["descripcion"],
                defaults={
                    "valor": recompensa_data["valor"],
                    "puntos_necesarios": recompensa_data["puntos"],
                },
            )

            if created:
                print(f"[SUCCESS] Recompensa creada: '{recompensa.descripcion}' (Nivel: {nivel}).")
            else:
                # Actualizar valores si ya existe
                recompensa.valor = recompensa_data["valor"]
                recompensa.puntos_necesarios = recompensa_data["puntos"]
                recompensa.save()
                print(f"[INFO] Recompensa actualizada: '{recompensa.descripcion}' (Nivel: {nivel}).")

            # Asociar recompensa al reto correspondiente en orden
            if recompensa_index < len(retos_nivel):
                reto_asociado = retos_nivel[recompensa_index]
                recompensa.reto = reto_asociado
                recompensa.save()
                print(f"[INFO] Recompensa '{recompensa.descripcion}' asociada al reto '{reto_asociado.nombre}'.")
                recompensa_index += 1
            else:
                print(f"[WARNING] No hay suficientes retos para asociar a la recompensa '{recompensa.descripcion}'.")

    print("[SUCCESS] Sincronización de recompensas globales completada.")


def sincronizar_y_asignar_recompensas(temporada_actual, usuario=None):
    """
    Sincroniza recompensas globales para la temporada actual y asigna las recompensas a los usuarios
    que cumplieron retos. Si se pasa un usuario específico, se asignan recompensas solo para ese usuario.
    """
    # Paso 1: Sincronizar recompensas globales
    sincronizar_recompensas_globales(temporada_actual)

    # Paso 2: Obtener usuarios técnicos (si no se especifica un usuario)
    usuarios = [usuario] if usuario else Usuario.objects.filter(rol__nombre="tecnico")

    for user in usuarios:
        print(f"[INFO] Procesando recompensas para el usuario '{user.username}'.")

        # Obtener retos cumplidos por el usuario en la temporada actual
        retos_cumplidos = RetoUsuario.objects.filter(
            usuario=user,
            cumplido=True,
            reto__temporada=temporada_actual,
        ).select_related('reto')

        for reto_usuario in retos_cumplidos:
            # Verificar si ya tiene una recompensa asignada
            recompensa_asignada = RecompensaUsuario.objects.filter(
                usuario=user,
                recompensa__reto=reto_usuario.reto
            ).exists()

            if not recompensa_asignada:
                # Buscar recompensa asociada al reto
                recompensa = Recompensa.objects.filter(
                    temporada=temporada_actual,
                    reto=reto_usuario.reto
                ).first()

                if recompensa:
                    # Asignar recompensa al usuario
                    RecompensaUsuario.objects.create(
                        usuario=user,
                        recompensa=recompensa,
                        redimido=False  # Inicialmente no redimida
                    )
                    print(f"[SUCCESS] Recompensa '{recompensa.descripcion}' asignada a '{user.username}'.")
                else:
                    print(f"[WARNING] No se encontró recompensa asociada al reto '{reto_usuario.reto.nombre}'.")

    print("[SUCCESS] Sincronización y asignación de recompensas completada.")

# Función para eliminar recompensas duplicadas
def eliminar_duplicados_globales(temporada_actual):
    """
    Elimina duplicados globales en recompensas para una temporada específica.
    """
    print("[INFO] Iniciando eliminación de recompensas duplicadas globales.")

    # Obtener todas las recompensas de la temporada actual
    recompensas = Recompensa.objects.filter(temporada=temporada_actual)

    # Identificar duplicados por tipo y descripción
    duplicados = (
        recompensas.values("tipo", "descripcion")
        .annotate(count=Count("id"))
        .filter(count__gt=1)
    )

    if not duplicados:
        print("[INFO] No se encontraron recompensas duplicadas.")
        return

    for duplicado in duplicados:
        tipo = duplicado["tipo"]
        descripcion = duplicado["descripcion"]

        # Buscar recompensas duplicadas y ordenar por ID para conservar la primera
        recompensas_a_eliminar = (
            Recompensa.objects.filter(
                temporada=temporada_actual, tipo=tipo, descripcion=descripcion
            )
            .order_by("id")[1:]  # Mantener solo la recompensa con el menor ID
        )

        # Eliminar recompensas duplicadas
        ids_eliminados = [recompensa.id for recompensa in recompensas_a_eliminar]
        recompensas_a_eliminar.delete()

        print(
            f"[SUCCESS] Recompensas duplicadas eliminadas para tipo '{tipo}' y descripción '{descripcion}'. IDs eliminados: {ids_eliminados}.")

    print("[SUCCESS] Eliminación de recompensas duplicadas completada.")
