from django.conf import settings
from django.db import models
from parties.models import Party

# 파티 채팅 메시지(일반/시스템)를 저장하는 모델
class ChatMessage(models.Model):
    # related_name="messages" 덕분에 Party 인스턴스에서 party.messages로 역참조할 수 있습니다.
    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name="messages")
    # 시스템 메시지는 user가 없을 수 있어 null/blank 허용
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_messages", null=True, blank=True)
    # True면 입장/퇴장/권한 변경 같은 시스템 메시지
    is_system = models.BooleanField(default=False)
    # user가 없거나 닉네임 스냅샷을 보존하고 싶을 때 사용
    sender_name = models.CharField(max_length=50, default="", blank=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # 파티별 시간순 조회가 잦아 복합 인덱스를 둡니다.
        indexes = [
            models.Index(fields=['party', 'created_at']),
        ]
        ordering = ["created_at"]

    def __str__(self) -> str:
        if self.is_system:
            return f"[SYSTEM] {self.content[:20]}"
        sender = self.sender_name or (self.user.nickname if self.user else "알 수 없음")
        return f"{sender}: {self.content[:20]}"