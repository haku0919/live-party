from django.urls import re_path
from . import consumers

# 채팅용 WebSocket URL임.
# asgi.py의 URLRouter가 이 패턴을 매칭하면 ChatConsumer로 연결함.
websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<party_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
]