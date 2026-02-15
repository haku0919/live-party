from django.contrib import admin
from .models import ChatMessage


# 관리자에서 채팅 로그를 탐색/검색하기 위한 설정
@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "party", "user", "short_content", "created_at")
    list_filter = ("party", "created_at")
    search_fields = ("content", "party__title", "user__username", "user__nickname")
    ordering = ("-id",)
    autocomplete_fields = ("party", "user")

    # 리스트에서 너무 긴 본문이 깨지지 않도록 축약 표시
    def short_content(self, obj):
        return obj.content[:30]
    short_content.short_description = "내용"