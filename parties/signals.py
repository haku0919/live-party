from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Party, PartyMember

@receiver(post_save, sender=PartyMember)
def handle_member_change(sender, instance, created, **kwargs):
    party = instance.party
    user = instance.user
    channel_layer = get_channel_layer()
    
    # 1. 인원수 업데이트
    active_count = party.members.filter(is_active=True).count()
    party.current_member_count = active_count
    
    if party.status != Party.Status.CLOSED:
        if party.current_member_count >= party.max_members:
            party.status = Party.Status.FULL
        else:
            party.status = Party.Status.OPEN
    party.save()

    # 2. 실시간 인원수 전송
    async_to_sync(channel_layer.group_send)(
        f"chat_{party.id}",
        {"type": "count_update", "count": party.current_member_count}
    )

    # 3. 시스템 메시지 생성
    user_name = getattr(user, 'nickname', user.username)
    message = None

    if created:
        message = f"📢 {user_name}님이 파티에 참여하셨습니다."
    elif not instance.is_active:
        message = f"🚪 {user_name}님이 파티를 떠났습니다."
    elif instance.is_active and not created:
        message = f"📢 {user_name}님이 다시 돌아왔습니다."

    if message:
        # ✅ consumer의 system_message 핸들러로 보냄
        async_to_sync(channel_layer.group_send)(
            f"chat_{party.id}",
            {
                "type": "system_message", 
                "message": message,
                "sender": "시스템" # 알림의 주체 명시
            }
        )

@receiver(post_save, sender=Party)
def broadcast_party_update(sender, instance, created, **kwargs):
    channel_layer = get_channel_layer()

    if instance.status == Party.Status.CLOSED:
        async_to_sync(channel_layer.group_send)(
            "lobby", {"type": "party_deleted", "party_id": instance.id}
        )
        async_to_sync(channel_layer.group_send)(
            f"chat_{instance.id}", {"type": "party_killed"}
        )
        return

    data = {
        "id": instance.id,
        "title": instance.title,
        "game": instance.game.name,
        "host": instance.host.nickname,
        "current_count": instance.current_member_count,
        "max_members": instance.max_members,
        "status": instance.get_status_display(),
    }
    async_to_sync(channel_layer.group_send)(
        "lobby",
        {"type": "party_update", "party_data": data, "is_new": created}
    )