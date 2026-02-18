import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatMessage
from parties.models import Party


class ChatConsumer(AsyncWebsocketConsumer):
    # 채팅 그룹 연결 및 인증을 처리함.
    async def connect(self):
        # routing.py의 (?P<party_id>\d+) 값을 URL kwargs에서 꺼냄.
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

    # 채팅 그룹 연결 해제를 처리함.
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # 채팅 메시지 수신 후 저장 및 브로드캐스트를 처리함.
    async def receive(self, text_data):
        # text_data는 브라우저에서 보낸 JSON 문자열임.
        data = json.loads(text_data)
        message = data['message']
        nickname = getattr(self.user, 'nickname', self.user.username)

        await self.save_message(message)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                # "type" 값과 같은 이름의 메서드(chat_message)가 자동 호출됨.
                'type': 'chat_message',
                'message': message,
                'sender': nickname,
                'sender_id': self.user.id
            }
        )

    # 메시지를 DB에 저장함.
    @database_sync_to_async
    def save_message(self, message):
        # ORM은 동기 코드이므로, async 컨슈머에서는 database_sync_to_async로 감쌈.
        try:
            party = Party.objects.get(id=self.room_name)
            ChatMessage.objects.create(
                party=party,
                user=self.user,
                content=message
            )
        except Party.DoesNotExist:
            # 방이 이미 삭제된 경우 저장을 건너뜀.
            pass

    # 일반 채팅 메시지를 클라이언트에 전달함.
    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    # 시스템 메시지를 클라이언트에 전달함.
    async def system_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'system_message',
            'message': event['message'],
        }))

    # 파티 해체 이벤트를 클라이언트에 전달함.
    async def party_killed(self, event):
        await self.send(text_data=json.dumps({
            'type': 'party_killed'
        }))

    # 강퇴 이벤트를 클라이언트에 전달함.
    async def user_kicked(self, event):
        await self.send(text_data=json.dumps({
            "type": "user_kicked",
            "kicked_user_id": event["kicked_user_id"],
            "kicked_user_name": event["kicked_user_name"]
        }))
    
    # 인원수 변경 이벤트를 클라이언트에 전달함.
    async def count_update(self, event):
        await self.send(text_data=json.dumps(event))

    # 활성 멤버 목록 업데이트 이벤트를 클라이언트에 전달함.
    async def member_list_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "member_list_update",
            "members": event["members"]
        }))        