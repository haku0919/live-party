from django.contrib.auth.models import AbstractUser
from django.db import models

# 서비스에서 사용하는 게임 목록을 관리하는 모델
class Game(models.Model):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=50)
    order = models.PositiveIntegerField(default=999)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

# 프로필 확장 필드를 포함한 커스텀 사용자 모델
class User(AbstractUser):
    class Gender(models.TextChoices):
        MALE = "MALE", "남"
        FEMALE = "FEMALE", "여"
        OTHER = "OTHER", "기타"
        PRIVATE = "PRIVATE", "비공개"

    class MicStatus(models.TextChoices):
        YES = "YES", "가능"
        NO = "NO", "불가능"

    nickname = models.CharField(
        max_length=15,
        unique=True,
    )

    phone = models.CharField(
        max_length=15,
        unique=True,
    )

    birth_year = models.IntegerField(
        help_text="출생년도 (예: 2002)",
    )

    gender = models.CharField(
        max_length=20,
        choices=Gender.choices,
    )

    mic_enabled = models.BooleanField(
        default=False,
        help_text="마이크 사용 가능 여부",
    )

    main_games = models.ManyToManyField(Game, blank=True, related_name="users")

    def __str__(self):
        return self.username