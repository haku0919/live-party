import json
import re

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from parties.models import Party, PartyMember

from .models import ChatMessage


class ChatConsumer(AsyncWebsocketConsumer):
    mention_pattern = re.compile(r"@([^\s@]{1,30})")

    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["party_id"]
        self.room_group_name = f"chat_{self.room_name}"
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = (data.get("message") or "").replace("\r", "").replace("\n", "").strip()
        if not message:
            return

        if not await self.can_chat():
            await self.send(text_data=json.dumps({"type": "chat_error", "message": "파티 참여자만 채팅할 수 있습니다."}))
            return

        mention_user_ids = await self.resolve_mentions(message)
        nickname = getattr(self.user, "nickname", self.user.username)

        saved = await self.save_message(message)
        if not saved:
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message_id": saved["id"],
                "message": message,
                "sender": nickname,
                "sender_id": self.user.id,
                "mention_user_ids": mention_user_ids,
            },
        )

    @database_sync_to_async
    def save_message(self, message):
        try:
            party = Party.objects.get(id=self.room_name)
            created = ChatMessage.objects.create(party=party, user=self.user, content=message)
            return {"id": created.id}
        except Party.DoesNotExist:
            return None

    @database_sync_to_async
    def can_chat(self):
        return PartyMember.objects.filter(
            party_id=self.room_name,
            user=self.user,
            is_active=True,
        ).exists()

    @database_sync_to_async
    def resolve_mentions(self, message):
        try:
            party = Party.objects.get(id=self.room_name)
        except Party.DoesNotExist:
            return []

        active_members = PartyMember.objects.filter(party=party, is_active=True).select_related("user")

        alias_to_user_id = {}
        for member in active_members:
            if member.user.nickname:
                alias_to_user_id[member.user.nickname.lower()] = member.user_id
            alias_to_user_id[member.user.username.lower()] = member.user_id

        mentioned_ids = set()
        for alias in self.mention_pattern.findall(message):
            user_id = alias_to_user_id.get(alias.lower())
            if user_id:
                mentioned_ids.add(user_id)

        return list(mentioned_ids)

    async def chat_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "chat_message",
                    "message_id": event.get("message_id"),
                    "message": event["message"],
                    "sender": event["sender"],
                    "sender_id": event["sender_id"],
                    "mention_user_ids": event.get("mention_user_ids", []),
                }
            )
        )

    async def system_message(self, event):
        payload = {"type": "system_message", "message": event["message"]}
        if "code" in event:
            payload["code"] = event["code"]
        if "actor_user_id" in event:
            payload["actor_user_id"] = event["actor_user_id"]
        await self.send(text_data=json.dumps(payload))

    async def party_killed(self, event):
        await self.send(text_data=json.dumps({"type": "party_killed"}))

    async def user_kicked(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "user_kicked",
                    "kicked_user_id": event["kicked_user_id"],
                    "kicked_user_name": event["kicked_user_name"],
                }
            )
        )

    async def count_update(self, event):
        await self.send(text_data=json.dumps(event))

    async def member_list_update(self, event):
        await self.send(text_data=json.dumps({"type": "member_list_update", "members": event["members"]}))

    async def join_request_update(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "join_request_update",
                    "action": event["action"],
                    "pending_count": event["pending_count"],
                    "request": event["request"],
                }
            )
        )

    async def join_request_result(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "join_request_result",
                    "target_user_id": event["target_user_id"],
                    "status": event["status"],
                    "message": event["message"],
                }
            )
        )

    async def waitlist_update(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "waitlist_update",
                    "count": event["count"],
                    "entries": event["entries"],
                }
            )
        )

    async def party_meta_update(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "party_meta_update",
                    "party": event["party"],
                }
            )
        )

    async def pinned_notice_update(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "pinned_notice_update",
                    "pinned": event.get("pinned"),
                }
            )
        )
