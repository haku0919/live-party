from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Game


# 관리자에서 Game 마스터 데이터를 관리함.
@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name")
    search_fields = ("code", "name")
    ordering = ("name",)


# 기본 UserAdmin을 확장해 커스텀 User 필드를 노출함.
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("추가 정보", {"fields": ("nickname", "phone", "birth_year", "gender", "mic_enabled", "main_games")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("추가 정보", {"fields": ("nickname", "phone", "birth_year", "gender", "mic_enabled", "main_games")}),
    )

    list_display = ("id", "username", "nickname", "phone", "gender", "birth_year", "is_staff", "is_active")
    search_fields = ("username", "nickname", "phone", "email")
    list_filter = ("gender", "is_staff", "is_active")
    ordering = ("-id",)

    filter_horizontal = ("main_games", "groups", "user_permissions")