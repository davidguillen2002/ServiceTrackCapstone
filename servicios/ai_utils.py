# servicios/ai_utils.py
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from ServiceTrack.models import Guia, Servicio  # Cambiar a ServiceTrack.models

def get_similar_guides(current_service):
    # Obtener todas las guías relacionadas con el tipo de equipo del servicio actual
    past_guides = Guia.objects.filter(equipo_marca=current_service.equipo.marca)

    # Obtener todos los servicios previos
    past_services = Servicio.objects.all()

    # Crear una lista de descripciones combinadas (incluyendo detalles del equipo y comentarios)
    descriptions = [f"{guide.descripcion} {guide.equipo_marca} {guide.equipo_modelo}" for guide in past_guides]
    descriptions += [f"{service.comentario_cliente} {service.equipo.marca} {service.equipo.modelo}" for service in past_services if service.comentario_cliente]

    # Agregar la descripción del servicio actual
    descriptions.append(f"{current_service.comentario_cliente} {current_service.equipo.marca} {current_service.equipo.modelo}")

    # Vectorización TF-IDF
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(descriptions)

    # Similitud coseno
    cosine_sim = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1])
    cosine_sim_list = cosine_sim[0].tolist()

    # Obtener las guías más similares (limitar solo a guías)
    similar_indices = sorted(range(len(cosine_sim_list)), key=lambda i: cosine_sim_list[i], reverse=True)[:5]
    similar_guides = [past_guides[idx] for idx in similar_indices if idx < len(past_guides)]

    return similar_guides