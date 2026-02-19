from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


# 파티 모집 정보와 상태를 관리하는 모델
class Party(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "모집중"
        FULL = "FULL", "마감"
        CLOSED = "CLOSED", "종료"

    class JoinPolicy(models.TextChoices):
        INSTANT = "INSTANT", "즉시 입장"
        APPROVAL = "APPROVAL", "승인제"

    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hosted_parties")
    game = models.ForeignKey("accounts.Game", on_delete=models.PROTECT, related_name="parties")
    mic_required = models.BooleanField(default=False, verbose_name="마이크 필수")

    mode = models.CharField(max_length=50, help_text="게임 모드 예: 랭크, 일반, 칼바람, 신속, 내전")
    description = models.TextField(blank=True)

    max_members = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(2), MaxValueValidator(20)],
        verbose_name="최대 인원",
    )
    join_policy = models.CharField(
        max_length=12,
        choices=JoinPolicy.choices,
        default=JoinPolicy.INSTANT,
        verbose_name="입장 방식",
    )
    pinned_message = models.ForeignKey(
        "chat.ChatMessage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pinned_parties",
    )
    pinned_updated_at = models.DateTimeField(null=True, blank=True)
    current_member_count = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


# 파티 참여 이력과 활성 상태를 관리하는 모델
class PartyMember(models.Model):
    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="party_memberships")
    joined_at = models.DateTimeField(auto_now_add=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["party", "user"], name="unique_party_member")]


# 파티별 재입장 제한 대상을 관리하는 모델
class BlackList(models.Model):
    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name="blacklist")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blacklisted_in_parties")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["party", "user"], name="unique_blacklist_entry")]


# 승인제 파티의 참가 신청 상태를 관리하는 모델
class PartyJoinRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "대기"
        APPROVED = "APPROVED", "수락"
        REJECTED = "REJECTED", "거절"
        CANCELLED = "CANCELLED", "취소"

    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name="join_requests")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="party_join_requests")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    requested_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decided_party_join_requests",
    )

    class Meta:
        ordering = ["requested_at"]
        constraints = [models.UniqueConstraint(fields=["party", "user"], name="unique_party_join_request")]


# 정원 초과 파티의 대기열을 관리하는 모델
class PartyWaitlist(models.Model):
    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name="waitlist_entries")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="party_waitlist_entries")
    queued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["queued_at"]
        constraints = [models.UniqueConstraint(fields=["party", "user"], name="unique_party_waitlist_entry")]
