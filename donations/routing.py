from django.urls import path

from .consumers import OverlayConsumer

websocket_urlpatterns = [
    path("ws/overlay/", OverlayConsumer.as_asgi()),
]
