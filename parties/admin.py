from django.contrib import admin
from .models import Party, PartyMember, BlackList


# 파티 목록 관리 화면을 구성함. 
@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    list_display = ("id", "game", "mode", "status", "host", "current_member_count", "max_members", "created_at")
    list_filter = ("game", "status", "mic_required", "created_at")

    search_fields = ("mode", "description", "host__username", "host__nickname", "game__name")

    ordering = ("-id",)
    autocomplete_fields = ("host", "game")


# 파티 멤버 관리 화면을 구성함.
@admin.register(PartyMember)
class PartyMemberAdmin(admin.ModelAdmin):
    list_display = ("id", "party", "user", "is_active", "joined_at")

    search_fields = ("party__mode", "user__username", "user__nickname")

    list_filter = ("is_active", "joined_at")
    ordering = ("-id",)
    autocomplete_fields = ("party", "user")


# 파티 블랙리스트 관리 화면을 구성함.
@admin.register(BlackList)
class PartyBlacklistAdmin(admin.ModelAdmin):
    list_display = ("id", "party", "user", "created_at")
    search_fields = ("party__mode", "user__username")
    list_filter = ("created_at",)
    ordering = ("-id",)
    autocomplete_fields = ("party", "user")