from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings

from . import reveal


class OverlayConsumer(AsyncJsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role = ""

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
        await reveal.drop_role(self.role)
        await self.channel_layer.group_discard("overlays", self.channel_name)

    async def receive_json(self, content, **kwargs):
        kind = content.get("type")
        role = content.get("role")
        if kind == "hello":
            self.role = role or ""
            await reveal.add_role(self.role)
            return
        if kind == "media_ready":
            await reveal.mark_ready(content.get("id"), role or self.role)

    async def donation_event(self, event):
        await self.send_json(event["payload"])

    @database_sync_to_async
    def _snapshot(self):
        from .models import SiteSettings
        from .realtime import snapshot_payload

        return snapshot_payload(SiteSettings.load())
