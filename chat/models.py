from django.conf import settings
from django.db import models
from parties.models import Party

class ChatMessage(models.Model):
    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name="messages")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_messages")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # ✅ 추가: 채팅 조회 속도 향상을 위한 인덱스 설정
        indexes = [
            models.Index(fields=['party', 'created_at']),
        ]
        ordering = ["created_at"] # id 대신 시간순 정렬이 더 안전함

    def __str__(self) -> str:
        return f"{self.user.nickname}: {self.content[:20]}"