from django.urls import re_path
from . import consumers

# ASGI(WebSocket) 라우팅입니다.
# asgi.py에서 parties.routing.websocket_urlpatterns + chat.routing.websocket_urlpatterns 형태로 합쳐집니다.
websocket_urlpatterns = [
    re_path(r'ws/lobby/$', consumers.LobbyConsumer.as_asgi()),
]