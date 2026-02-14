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

    # ---------------------------------------------------------
    # [기능 4 수신] 파티 카드 업데이트 (생성/수정)
    # signals.py의 [기능 4]에서 보낸 신호를 여기서 받습니다.
    # ---------------------------------------------------------
    async def party_update(self, event):
        # 브라우저에게 "새 파티 정보 줄게, 카드 만들거나 고쳐"라고 보냄
        # JS는 이걸 받아서 맨 앞에 새 카드를 끼워 넣음
        await self.send(text_data=json.dumps({
            "type": "party_update",
            "party_data": event["party_data"],
            "is_new": event["is_new"]
        }))

    # ---------------------------------------------------------
    # [기능 3-1 수신] 파티 카드 삭제
    # signals.py의 [기능 3]에서 보낸 신호를 여기서 받습니다.
    # ---------------------------------------------------------
    async def party_deleted(self, event):
        # 브라우저에게 "15번 파티 카드 화면에서 지워"라고 보냄
        # JS는 document.getElementById('card-15').remove() 실행
        await self.send(text_data=json.dumps({
            "type": "party_deleted",
            "party_id": event["party_id"]
        }))

    async def member_list_update(self, event):
        # signals.py에서 보낸 멤버 리스트(event["members"])를
        # 브라우저(HTML/JS)에게 그대로 전달합니다.
        await self.send(text_data=json.dumps({
            "type": "member_list_update",
            "members": event["members"]
        }))