from channels.generic.websocket import AsyncWebsocketConsumer
import json

class NotificacionesConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Obtener el grupo de notificaciones para el usuario basado en la URL
        self.usuario_id = self.scope["url_route"]["kwargs"]["usuario_id"]
        self.group_name = f"notificaciones_{self.usuario_id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        pass  # Manejo de mensajes entrantes si es necesario

    async def send_notification(self, event):
        """
        Maneja los mensajes enviados al grupo de notificaciones.
        """
        print(f"Notificación enviada: {event['data']}")  # Depuración
        await self.send(text_data=json.dumps(event["data"]))