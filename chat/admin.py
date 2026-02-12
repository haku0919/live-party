from django.contrib import admin
from .models import ChatMessage


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "party", "user", "short_content", "created_at")
    list_filter = ("party", "created_at")
    search_fields = ("content", "party__title", "user__username", "user__nickname")
    ordering = ("-id",)
    autocomplete_fields = ("party", "user")

    def short_content(self, obj):
        return obj.content[:30]
    short_content.short_description = "내용"