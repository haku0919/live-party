from django.contrib import admin
from .models import Party, PartyMember, BlackList


@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    # 'partyName'이 삭제되었으므로 'mode'를 주요 식별자로 사용합니다.
    list_display = ("id", "game", "mode", "status", "host", "current_member_count", "max_members", "created_at")
    list_filter = ("game", "status", "mic_required", "created_at")
    
    # ❌ search_fields에서 "partyName" 제거
    # ✅ "mode"와 "description" 위주로 검색되도록 수정
    search_fields = ("mode", "description", "host__username", "host__nickname", "game__name")
    
    ordering = ("-id",)
    autocomplete_fields = ("host", "game")


@admin.register(PartyMember)
class PartyMemberAdmin(admin.ModelAdmin):
    list_display = ("id", "party", "user", "is_active", "joined_at")
    
    # ❌ search_fields에서 "party__partyName" 제거
    search_fields = ("party__mode", "user__username", "user__nickname")
    
    list_filter = ("is_active", "joined_at")
    ordering = ("-id",)
    autocomplete_fields = ("party", "user")

@admin.register(BlackList)
class BlackListAdmin(admin.ModelAdmin):
    list_display = ("id", "party", "user", "created_at")
    search_fields = ("party__mode", "user__username")
    list_filter = ("created_at",)
    ordering = ("-id",)
    autocomplete_fields = ("party", "user")