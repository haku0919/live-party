from django.contrib import admin

from .models import BlackList, Party, PartyJoinRequest, PartyMember, PartyWaitlist


@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    list_display = ("id", "game", "mode", "status", "join_policy", "host", "current_member_count", "max_members", "created_at")
    list_filter = ("game", "status", "join_policy", "mic_required", "created_at")
    search_fields = ("mode", "description", "host__username", "host__nickname", "game__name")
    ordering = ("-id",)
    autocomplete_fields = ("host", "game")


@admin.register(PartyMember)
class PartyMemberAdmin(admin.ModelAdmin):
    list_display = ("id", "party", "user", "is_active", "joined_at")
    search_fields = ("party__mode", "user__username", "user__nickname")
    list_filter = ("is_active", "joined_at")
    ordering = ("-id",)
    autocomplete_fields = ("party", "user")


@admin.register(BlackList)
class PartyBlacklistAdmin(admin.ModelAdmin):
    list_display = ("id", "party", "user", "created_at")
    search_fields = ("party__mode", "user__username")
    list_filter = ("created_at",)
    ordering = ("-id",)
    autocomplete_fields = ("party", "user")


@admin.register(PartyJoinRequest)
class PartyJoinRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "party", "user", "status", "requested_at", "decided_at", "decided_by")
    list_filter = ("status", "requested_at", "decided_at")
    search_fields = ("party__mode", "user__username", "user__nickname")
    ordering = ("-id",)
    autocomplete_fields = ("party", "user", "decided_by")


@admin.register(PartyWaitlist)
class PartyWaitlistAdmin(admin.ModelAdmin):
    list_display = ("id", "party", "user", "queued_at")
    list_filter = ("queued_at",)
    search_fields = ("party__mode", "user__username", "user__nickname")
    ordering = ("-id",)
    autocomplete_fields = ("party", "user")
