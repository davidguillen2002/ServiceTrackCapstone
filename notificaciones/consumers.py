# notificaciones/consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
import json

class NotificacionesConsumer(AsyncWebsocketConsumer):
    async def connect(self):
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

    async def send_notification(self, event):
        # Enviar notificación al cliente conectado
        await self.send(text_data=json.dumps(event["data"]))