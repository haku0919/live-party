from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Party, PartyMember

# ===== 시그널 ↔ 컨슈머 연결 지도 =====
# group_send(..., {"type": "count_update"})        -> chat/consumers.py::ChatConsumer.count_update
# group_send(..., {"type": "member_list_update"})  -> chat/consumers.py::ChatConsumer.member_list_update
# group_send(..., {"type": "system_message"})      -> chat/consumers.py::ChatConsumer.system_message
# group_send("lobby", {"type": "party_update"})   -> parties/consumers.py::LobbyConsumer.party_update
# group_send("lobby", {"type": "party_deleted"})  -> parties/consumers.py::LobbyConsumer.party_deleted
# group_send(..., {"type": "party_killed"})        -> chat/consumers.py::ChatConsumer.party_killed

# PartyMember 저장 직후 실행되어, 파티의 실시간 상태를 동기화하는 시그널 핸들러임.
#
# 이 함수가 하는 일:
# 1) 방장 이탈 시 새 방장 자동 위임
# 2) 현재 인원수/모집 상태 업데이트
# 3) 채팅방에 count_update, member_list_update 이벤트 전송
# 4) 입장/퇴장/재입장 시스템 메시지 전송
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

    # 채팅 화면 상단 인원수 배지를 즉시 갱신함.
    # (프론트 수신 위치: parties/templates/parties/party_detail.html)
    async_to_sync(channel_layer.group_send)(
        f"chat_{party.id}",
        {"type": "count_update", "count": party.current_member_count}
    )

    # 채팅 우측 멤버 목록 렌더링용 데이터 구성
    active_members = party.members.filter(is_active=True).select_related('user').order_by('joined_at')

    members_data = []
    for member in active_members:
        members_data.append({
            'id': member.user.id,
            'nickname': member.user.nickname,
            'is_host': (member.user == party.host)
        })

    # 프론트는 이 이벤트를 받아 멤버 리스트/왕관/강퇴버튼 표시를 다시 그림.
    # (수신 메서드: ChatConsumer.member_list_update)
    async_to_sync(channel_layer.group_send)(
        f"chat_{party.id}",
        {
            "type": "member_list_update",
            "members": members_data
        }
    )

    # 시스템 메시지 문구 선택
    user_name = getattr(user, 'nickname', user.username)
    message = None

    if created:
        message = f"📢 {user_name}님이 파티에 참여하셨습니다."
    elif not instance.is_active and not kicked_by_host:
        # 강퇴는 별도 이벤트로 안내하므로 일반 퇴장 메시지는 생략
        message = f"🚪 {user_name}님이 파티를 떠났습니다."
    elif instance.is_active and not created:
        message = f"📢 {user_name}님이 다시 돌아왔습니다."

    # 선택된 시스템 메시지를 채팅방으로 전송
    # (수신 메서드: ChatConsumer.system_message)
    if message:
        async_to_sync(channel_layer.group_send)(
            f"chat_{party.id}",
            {
                "type": "system_message", 
                "message": message,
                "sender": "시스템"
            }
        )

    # 새 방장 지정이 발생했으면 별도 공지 메시지를 보냄.
    # (수신 메서드: ChatConsumer.system_message)
    if new_host_name:
        async_to_sync(channel_layer.group_send)(
            f"chat_{party.id}",
            {
                "type": "system_message",
                "message": f"👑 {new_host_name}님이 새로운 방장이 되었습니다.",
                "sender": "시스템"
            }
        )

# Party 저장 직후 실행되어, 로비 카드/채팅방 종료 이벤트를 동기화하는 시그널 핸들러임.
@receiver(post_save, sender=Party)
def broadcast_party_update(sender, instance, created, **kwargs):
    channel_layer = get_channel_layer()

    # 종료 상태면 로비 카드 삭제 + 채팅방 종료 이벤트를 보냄.
    if instance.status == Party.Status.CLOSED:
        # 수신 메서드: LobbyConsumer.party_deleted
        async_to_sync(channel_layer.group_send)(
            "lobby", {"type": "party_deleted", "party_id": instance.id}
        )

        # 수신 메서드: ChatConsumer.party_killed
        async_to_sync(channel_layer.group_send)(
            f"chat_{instance.id}", {"type": "party_killed"}
        )
        return

    # 로비 카드 업데이트에 필요한 최소 데이터만 전송함.
    data = {
        "id": instance.id,
        "title": instance.mode,
        "game": instance.game.name,
        "host": instance.host.nickname if instance.host.nickname else instance.host.username,
        "current_count": instance.current_member_count,
        "max_members": instance.max_members,
        "status": instance.get_status_display(),
    }

    # 생성/수정 모두 party_update로 처리하고, is_new 플래그로 프론트 분기
    # 수신 메서드: LobbyConsumer.party_update
    async_to_sync(channel_layer.group_send)(
        "lobby",
        {"type": "party_update", "party_data": data, "is_new": created}
    )