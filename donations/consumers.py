from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings


class OverlayConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        query = parse_qs(self.scope.get("query_string", b"").decode())
        key = (query.get("key") or [""])[0]
        expected = settings.OVERLAY_TOKEN
        if expected and key != expected:
            await self.close(code=4401)
            return
        await self.channel_layer.group_add("overlays", self.channel_name)
        await self.accept()
        snapshot = await self._snapshot()
        await self.send_json(snapshot)

    async def disconnect(self, code):
        await self.channel_layer.group_discard("overlays", self.channel_name)

    async def donation_event(self, event):
        await self.send_json(event["payload"])

    @database_sync_to_async
    def _snapshot(self):
        from .models import SiteSettings
        from .realtime import snapshot_payload

        return snapshot_payload(SiteSettings.load())
