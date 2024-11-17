from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/notificaciones/<int:usuario_id>/', consumers.NotificacionesConsumer.as_asgi()),
]
