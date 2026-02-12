from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

# -----------------------------
# 게임 목록 모델
# -----------------------------
class Game(models.Model):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=50)
    order = models.PositiveIntegerField(default=999)  # 작을수록 앞에 표시

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


# -----------------------------
# 커스텀 유저 모델
# -----------------------------
class User(AbstractUser):
    class Gender(models.TextChoices):
        MALE = "MALE", "남"
        FEMALE = "FEMALE", "여"
        OTHER = "OTHER", "기타"
        PRIVATE = "PRIVATE", "비공개"

    class MicStatus(models.TextChoices):
        YES = "YES", "가능"
        NO = "NO", "불가능"

    # 닉네임 (중복 불가)
    nickname = models.CharField(
        max_length=15,
        unique=True,
    )

    # 전화번호 (중복 불가)
    phone = models.CharField(
        max_length=15,
        unique=True,
    )

    # 출생년도 (필수 입력, 유효성 검사는 폼에서 정밀하게 처리)
    birth_year = models.IntegerField(
        help_text="출생년도 (예: 2002)",
    )

    # 성별
    gender = models.CharField(
        max_length=20,
        choices=Gender.choices,
    )

    # 마이크 사용 여부 (기본값 False)
    mic_enabled = models.BooleanField(
        default=False,
        help_text="마이크 사용 가능 여부",
    )

    # 주로 하는 게임 (다중 선택)
    main_games = models.ManyToManyField(Game, blank=True, related_name="users")

    def __str__(self):
        return self.username