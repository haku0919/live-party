from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Party(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "모집중"
        FULL = "FULL", "마감"
        CLOSED = "CLOSED", "종료"

    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hosted_parties")
    # Game 모델이 accounts 앱에 있다면 문자열로 참조해야 순환참조가 안 생깁니다.
    game = models.ForeignKey("accounts.Game", on_delete=models.PROTECT, related_name="parties")
    mic_required = models.BooleanField(default=False, verbose_name="마이크 필수")
    
    mode = models.CharField(max_length=50, help_text="게임 모드 예: 랭크, 일반, 칼바람, 신속, 내전")
    description = models.TextField(blank=True)
    
    max_members = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(2), MaxValueValidator(20)],
        verbose_name="최대 인원"
    )
    current_member_count = models.PositiveIntegerField(default=1)    
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.game.name}] {self.mode} - {self.host.nickname|default:self.host.username}"  

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

class BlackList(models.Model):
    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name="blacklist")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blacklisted_in_parties")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["party", "user"], name="unique_blacklist_entry")
        ]