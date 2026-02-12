# parties/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class LobbyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # 로비 그룹("lobby")에 참여
        await self.channel_layer.group_add("lobby", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # 로비 그룹에서 퇴장
        await self.channel_layer.group_discard("lobby", self.channel_name)

    # signals.py에서 "새 파티 생김/변경됨" 신호를 받으면 프론트엔드로 전달
    async def party_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "party_update",
            "party_data": event["party_data"],
            "is_new": event["is_new"]
        }))

    # signals.py에서 "파티 삭제됨" 신호를 받으면 프론트엔드로 전달
    async def party_deleted(self, event):
        await self.send(text_data=json.dumps({
            "type": "party_deleted",
            "party_id": event["party_id"]
        }))