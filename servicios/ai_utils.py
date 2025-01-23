from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from ServiceTrack.models import Guia, Servicio

# Cargar un modelo preentrenado de embeddings semánticos
model = SentenceTransformer('all-MiniLM-L6-v2')

def get_similar_guides(current_service):
    # Obtener guías relevantes relacionadas con el equipo del servicio actual
    past_guides = list(Guia.objects.filter(equipo_marca=current_service.equipo.marca))  # Convertir a lista

    # Obtener servicios previos de la base de datos
    past_services = list(Servicio.objects.all())  # Convertir a lista

    # Construir descripciones de guías y servicios
    guide_texts = [
        f"{guide.descripcion} {guide.equipo_marca} {guide.equipo_modelo} {guide.categoria.nombre if guide.categoria else ''}"
        for guide in past_guides
    ]
    service_texts = [
        f"{service.comentario_cliente or ''} {service.equipo.marca} {service.equipo.modelo} {service.estado}"
        for service in past_services
    ]

    # Descripción del servicio actual
    current_text = f"{current_service.comentario_cliente or ''} {current_service.equipo.marca} {current_service.equipo.modelo}"

    # Crear una lista con todas las descripciones
    all_texts = guide_texts + service_texts + [current_text]

    # Generar embeddings para todos los textos
    embeddings = model.encode(all_texts)

    # Calcular similitudes entre el servicio actual y los textos existentes
    current_embedding = embeddings[-1].reshape(1, -1)  # Embedding del servicio actual
    similarities = cosine_similarity(current_embedding, embeddings[:-1]).flatten()

    # Extraer las similitudes correspondientes a las guías
    guide_similarities = similarities[:len(guide_texts)]
    similar_indices = guide_similarities.argsort()[-5:][::-1]  # Índices de guías más similares

    # Seleccionar guías más relevantes
    similar_guides = [past_guides[int(i)] for i in similar_indices]  # Asegurarse de convertir a `int`

    return similar_guides


def get_similar_guides_with_context(current_service, tecnico):
    # Obtener guías relacionadas con el equipo del servicio actual
    past_guides = list(Guia.objects.filter(equipo_marca=current_service.equipo.marca))  # Convertir a lista

    # Obtener servicios previos relacionados con el técnico actual
    past_services = list(Servicio.objects.filter(tecnico=tecnico))  # Convertir a lista

    # Construir descripciones de guías y servicios con contexto adicional
    guide_texts = [
        f"{guide.descripcion} {guide.equipo_marca} {guide.equipo_modelo} {guide.categoria.nombre if guide.categoria else ''}"
        for guide in past_guides
    ]
    service_texts = [
        f"{service.comentario_cliente or ''} {service.equipo.marca} {service.equipo.modelo} {service.estado}"
        for service in past_services
    ]

    # Texto del servicio actual
    current_text = f"{current_service.comentario_cliente or ''} {current_service.equipo.marca} {current_service.equipo.modelo}"

    # Combinar todas las descripciones
    all_texts = guide_texts + service_texts + [current_text]

    # Generar embeddings para todos los textos
    embeddings = model.encode(all_texts)

    # Calcular similitudes entre el servicio actual y los textos existentes
    current_embedding = embeddings[-1].reshape(1, -1)
    similarities = cosine_similarity(current_embedding, embeddings[:-1]).flatten()

    # Clasificar y seleccionar las guías más relevantes
    guide_similarities = similarities[:len(guide_texts)]
    similar_indices = guide_similarities.argsort()[-5:][::-1]
    similar_guides = [past_guides[int(i)] for i in similar_indices]  # Asegurarse de convertir a `int`

    return similar_guides