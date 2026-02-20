from django.db import transaction as db_transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Party, PartyMember

@receiver(post_save, sender=PartyMember)
def handle_member_change(sender, instance, created, **kwargs):
    # instance는 "방금 저장된 PartyMember 한 건"임.
    party = instance.party
    user = instance.user
    # 강퇴에서 온 비활성화인지 구분하기 위한 임시 플래그(뷰에서 주입)
    kicked_by_host = getattr(instance, "_kicked", False)
    channel_layer = get_channel_layer()

    # 방장 본인이 비활성화되면(=나가기), 자동 위임 로직을 수행함.
    host_left = (instance.user_id == party.host_id and not instance.is_active)
    new_host_name = None

    if host_left:
        # joined_at 오름차순 = 가장 먼저 들어온 활성 멤버가 우선권
        successor = (
            party.members
            .filter(is_active=True)
            .exclude(user_id=instance.user_id)
            .select_related('user')
            .order_by('joined_at')
            .first()
        )
        if successor:
            # 새 방장 지정
            party.host = successor.user
            new_host_name = successor.user.nickname or successor.user.username
        else:
            # 남은 사람이 없으면 파티 종료 상태로 전환
            party.status = Party.Status.CLOSED

    # 현재 활성 인원을 다시 계산해 파티 스냅샷을 최신화함.
    active_count = party.members.filter(is_active=True).count()
    party.current_member_count = active_count

    # CLOSED가 아니라면 인원수 기준으로 OPEN/FULL을 자동 전환함.
    if party.status != Party.Status.CLOSED:
        if party.current_member_count >= party.max_members:
            party.status = Party.Status.FULL
        else:
            party.status = Party.Status.OPEN

    # host/status/count 변경사항을 실제 DB에 반영
    party.save()

    # --- WebSocket 브로드캐스트 데이터를 미리 수집 ---
    party_id = party.id
    count = party.current_member_count

    active_members = party.members.filter(is_active=True).select_related('user').order_by('joined_at')
    members_data = [
        {
            'id': member.user.id,
            'nickname': member.user.nickname if member.user.nickname else member.user.username,
            'is_host': (member.user_id == party.host_id),
        }
        for member in active_members
    ]

    user_name = getattr(user, 'nickname', None) or user.username
    system_message = None

    if created:
        system_message = f"📢 {user_name}님이 파티에 참여하셨습니다."
    elif not instance.is_active and not kicked_by_host:
        # 강퇴는 별도 이벤트로 안내하므로 일반 퇴장 메시지만
        system_message = f"🚪 {user_name}님이 파티를 떠났습니다."
    elif instance.is_active and not created:
        system_message = f"📢 {user_name}님이 다시 돌아왔습니다."

    new_host_msg = f"👑 {new_host_name}님이 새로운 방장이 되었습니다." if new_host_name else None

    # 트랜잭션 커밋 후에 WebSocket 메시지를 전송
    # → 롤백 시 잘못된 메시지가 전송되는 문제를 방지
    def _send(
        _party_id=party_id,
        _count=count,
        _members_data=members_data,
        _system_message=system_message,
        _new_host_msg=new_host_msg,
        _channel_layer=channel_layer,
    ):
        async_to_sync(_channel_layer.group_send)(
            f"chat_{_party_id}",
            {"type": "count_update", "count": _count},
        )
        async_to_sync(_channel_layer.group_send)(
            f"chat_{_party_id}",
            {"type": "member_list_update", "members": _members_data},
        )
        if _system_message:
            async_to_sync(_channel_layer.group_send)(
                f"chat_{_party_id}",
                {"type": "system_message", "message": _system_message, "sender": "시스템"},
            )
        if _new_host_msg:
            async_to_sync(_channel_layer.group_send)(
                f"chat_{_party_id}",
                {"type": "system_message", "message": _new_host_msg, "sender": "시스템"},
            )

    db_transaction.on_commit(_send)


# Party 저장 직후 실행되어, 로비 카드/채팅방 종료 이벤트를 동기화하는 시그널 핸들러임.
@receiver(post_save, sender=Party)
def broadcast_party_update(sender, instance, created, **kwargs):
    channel_layer = get_channel_layer()
    party_id = instance.id

    # 종료 상태면 로비 카드 삭제 + 채팅방 종료 이벤트를 보냄.
    if instance.status == Party.Status.CLOSED:
        def _send_closed(
            _party_id=party_id,
            _channel_layer=channel_layer,
        ):
            async_to_sync(_channel_layer.group_send)(
                "lobby", {"type": "party_deleted", "party_id": _party_id}
            )
            async_to_sync(_channel_layer.group_send)(
                f"chat_{_party_id}", {"type": "party_killed"}
            )
        db_transaction.on_commit(_send_closed)
        return

    # 로비 카드 업데이트에 필요한 최소 데이터만 전송함.
    data = {
        "id": instance.id,
        "title": instance.mode,
        "game": instance.game.name,
        "host": instance.host.nickname if instance.host.nickname else instance.host.username,
        "description": instance.description or "",
        "mic_required": instance.mic_required,
        "join_policy": instance.join_policy,
        "current_count": instance.current_member_count,
        "max_members": instance.max_members,
        "status": instance.get_status_display(),
        "status_code": instance.status,
    }
    is_new = created

    # 생성/수정 모두 party_update로 처리하고, is_new 플래그로 프론트 분기
    def _send(
        _party_id=party_id,
        _data=data,
        _is_new=is_new,
        _channel_layer=channel_layer,
    ):
        async_to_sync(_channel_layer.group_send)(
            "lobby",
            {"type": "party_update", "party_data": _data, "is_new": _is_new},
        )
        async_to_sync(_channel_layer.group_send)(
            f"chat_{_party_id}",
            {"type": "party_meta_update", "party": _data},
        )

    db_transaction.on_commit(_send)
