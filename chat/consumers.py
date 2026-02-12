import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['party_id']
        self.room_group_name = f'chat_{self.room_name}'
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # 연결만 끊고 DB는 건드리지 않음
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        nickname = getattr(self.user, 'nickname', self.user.username)

        # 일반 채팅 메시지 전송
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender': nickname,
                'sender_id': self.user.id
            }
        )

    # [핸들러] 일반 채팅
    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    # [핸들러] 시스템 알림 (입퇴장 등)
    async def system_message(self, event):
        # sender 없이 message만 보냄 (JS에서 디자인 분리 처리)
        await self.send(text_data=json.dumps({
            'type': 'system_message',
            'message': event['message'],
        }))

    # [핸들러] 파티 종료 알림
    async def party_killed(self, event):
        await self.send(text_data=json.dumps({
            'type': 'party_killed'
        }))
    
    # [핸들러] 인원수 업데이트
    async def count_update(self, event):
        await self.send(text_data=json.dumps(event))