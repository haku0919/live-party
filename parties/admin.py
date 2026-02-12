from django.contrib import admin
from .models import Party, PartyMember


@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "game", "mode", "status", "host", "max_members", "created_at")
    list_filter = ("game", "mode", "status", "created_at")
    search_fields = ("title", "description", "host__username", "host__nickname", "game__code", "game__name")
    ordering = ("-id",)
    autocomplete_fields = ("host", "game")


@admin.register(PartyMember)
class PartyMemberAdmin(admin.ModelAdmin):
    list_display = ("id", "party", "user", "joined_at")
    search_fields = ("party__title", "user__username", "user__nickname")
    ordering = ("-id",)
    autocomplete_fields = ("party", "user")