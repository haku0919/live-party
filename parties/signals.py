# parties/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Party, PartyMember

# =============================================================================
# [기능 A] 멤버가 들어오거나 나갈 때 (입/퇴장 알림 & 인원수 갱신)
# 🔍 감지 대상: PartyMember 테이블 (누가 파티에 가입하거나 탈퇴할 때)
# =============================================================================
@receiver(post_save, sender=PartyMember)
def handle_member_change(sender, instance, created, **kwargs):
    party = instance.party
    user = instance.user
    channel_layer = get_channel_layer() # 방송 장비(Channel Layer) 가져오기
    
    # [A-1] DB 정리: 현재 인원수 다시 세서 저장
    # (누가 들어왔으니 숫자를 업데이트해야 함)
    active_count = party.members.filter(is_active=True).count()
    party.current_member_count = active_count
    
    # 인원수에 따라 '모집중' vs '마감' 상태 자동 변경
    if party.status != Party.Status.CLOSED:
        if party.current_member_count >= party.max_members:
            party.status = Party.Status.FULL
        else:
            party.status = Party.Status.OPEN
    party.save()

    # -------------------------------------------------------------------------
    # [신호 1] "인원수 변경됨" 방송 송출
    # 📡 수신처: chat/consumers.py의 `count_update` 함수
    # 목적: 채팅방 상단에 있는 "3/5명" 같은 숫자를 실시간으로 바꾸기 위해
    # -------------------------------------------------------------------------
    async_to_sync(channel_layer.group_send)(
        f"chat_{party.id}", # 방송할 채널 그룹 이름 (예: chat_1번방)
        {"type": "count_update", "count": party.current_member_count}
    )

    # ============================================================
    # ✅ [여기부터 추가된 부분] 실시간 멤버 리스트 전송 로직
    # ============================================================
    # (1) 현재 활동 중인 멤버들을 싹 긁어옵니다.
    active_members = party.members.filter(is_active=True).select_related('user')
    
    # (2) 방송으로 보낼 수 있게 리스트(딕셔너리 형태)로 변환합니다.
    members_data = []
    for member in active_members:
        members_data.append({
            'id': member.user.id,
            'nickname': member.user.nickname,
            'is_host': (member.user == party.host)  # 방장인지 표시
        })
        
    # (3) "멤버 리스트 이걸로 싹 교체해!"라고 방송을 보냅니다.
    async_to_sync(channel_layer.group_send)(
        f"chat_{party.id}",
        {
            "type": "member_list_update",  # Consumer에 이 함수(기능)를 추가해야 함
            "members": members_data
        }
    )

    # -------------------------------------------------------------------------
    # [신호 2] "입장/퇴장 알림" 메시지 생성 및 방송 송출
    # 📡 수신처: chat/consumers.py의 `system_message` 함수
    # 목적: 채팅창에 회색 글씨로 "00님이 입장했습니다"를 띄우기 위해
    # -------------------------------------------------------------------------
    user_name = getattr(user, 'nickname', user.username)
    message = None

    if created:
        # DB에 새로 생성됨 = "신규 입장"
        message = f"📢 {user_name}님이 파티에 참여하셨습니다."
    elif not instance.is_active:
        # DB에는 있는데 active가 꺼짐 = "퇴장 (나가기)"
        message = f"🚪 {user_name}님이 파티를 떠났습니다."
    elif instance.is_active and not created:
        # 나갔던 사람이 active를 다시 켬 = "재입장"
        message = f"📢 {user_name}님이 다시 돌아왔습니다."

    if message:
        async_to_sync(channel_layer.group_send)(
            f"chat_{party.id}",
            {
                "type": "system_message", 
                "message": message,
                "sender": "시스템"
            }
        )

# =============================================================================
# [기능 B] 파티 정보가 바뀌거나 폭파될 때 (로비 카드 갱신)
# 🔍 감지 대상: Party 테이블 (파티 제목 수정, 방 삭제 등)
# =============================================================================
@receiver(post_save, sender=Party)
def broadcast_party_update(sender, instance, created, **kwargs):
    channel_layer = get_channel_layer()

    # [B-1] 파티가 '종료(CLOSED)' 상태가 된 경우 (방장이 해체함)
    if instance.status == Party.Status.CLOSED:
        # ---------------------------------------------------------------------
        # [신호 3] "파티 삭제됨" 방송 송출 (로비용)
        # 📡 수신처: parties/consumers.py의 `party_deleted` 함수
        # 목적: 로비 목록에서 해당 파티 카드를 슉 없애버리기 위해
        # ---------------------------------------------------------------------
        async_to_sync(channel_layer.group_send)(
            "lobby", {"type": "party_deleted", "party_id": instance.id}
        )
        
        # ---------------------------------------------------------------------
        # [신호 4] "파티 폭파됨" 방송 송출 (채팅방용)
        # 📡 수신처: chat/consumers.py의 `party_killed` 함수
        # 목적: 채팅방에 있는 사람들에게 "방 끝났으니 나가세요" 팝업을 띄우기 위해
        # ---------------------------------------------------------------------
        async_to_sync(channel_layer.group_send)(
            f"chat_{instance.id}", {"type": "party_killed"}
        )
        return

    # [B-2] 파티가 새로 생겼거나, 제목/인원수 정보가 바뀐 경우
    data = {
        "id": instance.id,
        "title": instance.mode,
        "game": instance.game.name,
        "host": instance.host.nickname if instance.host.nickname else instance.host.username,
        "current_count": instance.current_member_count,
        "max_members": instance.max_members,
        "status": instance.get_status_display(),
    }
    
    # -------------------------------------------------------------------------
    # [신호 5] "파티 정보 업데이트" 방송 송출
    # 📡 수신처: parties/consumers.py의 `party_update` 함수
    # 목적: 로비 맨 앞에 새 카드를 추가하거나, 기존 카드의 내용을 고치기 위해
    # -------------------------------------------------------------------------
    async_to_sync(channel_layer.group_send)(
        "lobby",
        {"type": "party_update", "party_data": data, "is_new": created}
    )