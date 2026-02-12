from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Party(models.Model):
    class Mode(models.TextChoices):
        RANK = "RANK", "랭크"
        NORMAL = "NORMAL", "일반(비랭크)"
        CUSTOM = "CUSTOM", "내전"
        ETC = "ETC", "기타"

    class Status(models.TextChoices):
        OPEN = "OPEN", "모집중"
        FULL = "FULL", "마감"
        CLOSED = "CLOSED", "종료"

    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hosted_parties")
    # Game 모델이 accounts 앱에 있다면 문자열로 참조해야 순환참조가 안 생깁니다.
    game = models.ForeignKey("accounts.Game", on_delete=models.PROTECT, related_name="parties")
    
    mode = models.CharField(max_length=20, choices=Mode.choices, default=Mode.NORMAL)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    max_members = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(2), MaxValueValidator(20)],
        verbose_name="최대 인원"
    )
    current_member_count = models.PositiveIntegerField(default=0)
    
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.game.name}] {self.title}"


class PartyMember(models.Model):
    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="party_memberships")
    joined_at = models.DateTimeField(auto_now_add=True)
    
    # True=참여중, False=나감(기록용)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["party", "user"], name="unique_party_member")
        ]