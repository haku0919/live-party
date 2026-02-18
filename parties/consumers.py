import json
from channels.generic.websocket import AsyncWebsocketConsumer

# 로비 페이지에서 사용하는 WebSocket Consumer임.
# 서버가 보낸 이벤트를 프론트가 그릴 수 있는 JSON 형태로 중계함.
#
# 이벤트 발신자(주로): parties/signals.py::broadcast_party_update
# - type="party_update"  -> 이 파일의 party_update 메서드로 라우팅
# - type="party_deleted" -> 이 파일의 party_deleted 메서드로 라우팅
class LobbyConsumer(AsyncWebsocketConsumer):
    # 소켓 연결 시 "lobby" 그룹에 현재 클라이언트 채널을 등록함.
    async def connect(self):
        # group_add("lobby", channel_name): "lobby" 브로드캐스트를 이 클라이언트가 받게 함
        await self.channel_layer.group_add("lobby", self.channel_name)
        await self.accept()

    # 브라우저가 떠나면 그룹에서 채널을 제거해 누수/중복 전송을 방지함.
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("lobby", self.channel_name)

    # 파티 카드 생성/수정 이벤트를 그대로 브라우저로 전달함.
    async def party_update(self, event):
        # event["party_data"]는 signals.py에서 만든 카드 렌더링용 요약 데이터
        await self.send(text_data=json.dumps({
            "type": "party_update",
            "party_data": event["party_data"],
            "is_new": event["is_new"]
        }))

    # 파티 카드 삭제 이벤트를 전달함.
    async def party_deleted(self, event):
        await self.send(text_data=json.dumps({
            "type": "party_deleted",
            "party_id": event["party_id"]
        }))

    # 활성 멤버 목록 변경 이벤트를 전달함.
    async def member_list_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "member_list_update",
            "members": event["members"]
        }))