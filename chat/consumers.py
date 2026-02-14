import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatMessage
from parties.models import Party

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
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        nickname = getattr(self.user, 'nickname', self.user.username)

        await self.save_message(message)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender': nickname,
                'sender_id': self.user.id
            }
        )

    @database_sync_to_async
    def save_message(self, message):
        try:
            party = Party.objects.get(id=self.room_name)
            ChatMessage.objects.create(
                party=party,
                user=self.user,
                content=message
            )
        except Party.DoesNotExist:
            pass

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    async def system_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'system_message',
            'message': event['message'],
        }))

    async def party_killed(self, event):
        await self.send(text_data=json.dumps({
            'type': 'party_killed'
        }))
    
    async def count_update(self, event):
        await self.send(text_data=json.dumps(event))

    # ============================================================
    # ✅ [여기부터 추가된 부분] 실시간 멤버 리스트 업데이트 함수
    # ============================================================
    async def member_list_update(self, event):
        # signals.py에서 보낸 멤버 리스트(event["members"])를
        # 브라우저(HTML/JS)에게 그대로 전달합니다.
        await self.send(text_data=json.dumps({
            "type": "member_list_update",
            "members": event["members"]
        }))
    # ============================================================
    # ✅ [여기까지 추가 끝]
    # ============================================================