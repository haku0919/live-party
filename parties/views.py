from urllib.parse import quote

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, View

from accounts.mixins import VerifiedEmailRequiredMixin
from chat.models import ChatMessage
from .forms import PartyForm
from .mixins import NotInBlackListMixin
from .models import BlackList, Party, PartyJoinRequest, PartyMember, PartyWaitlist


def _display_name(user):
    return user.nickname if user.nickname else user.username


def _waitlist_rank(party, user_id):
    for idx, uid in enumerate(party.waitlist_entries.order_by("queued_at").values_list("user_id", flat=True), start=1):
        if uid == user_id:
            return idx
    return None


def _broadcast_member_snapshot(party):
    channel_layer = get_channel_layer()

    active_members = party.members.filter(is_active=True).select_related("user").order_by("joined_at")
    members_data = [
        {
            "id": member.user.id,
            "nickname": _display_name(member.user),
            "is_host": member.user_id == party.host_id,
        }
        for member in active_members
    ]

    async_to_sync(channel_layer.group_send)(
        f"chat_{party.id}",
        {
            "type": "member_list_update",
            "members": members_data,
        },
    )

    async_to_sync(channel_layer.group_send)(
        f"chat_{party.id}",
        {
            "type": "count_update",
            "count": party.current_member_count,
        },
    )


def _broadcast_waitlist_update(party):
    channel_layer = get_channel_layer()
    wait_entries = list(party.waitlist_entries.select_related("user").order_by("queued_at"))

    data = [
        {
            "user_id": entry.user_id,
            "nickname": _display_name(entry.user),
            "rank": idx,
        }
        for idx, entry in enumerate(wait_entries, start=1)
    ]

    async_to_sync(channel_layer.group_send)(
        f"chat_{party.id}",
        {
            "type": "waitlist_update",
            "count": len(wait_entries),
            "entries": data,
        },
    )


def _broadcast_join_request_update(party, action, join_request):
    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        f"chat_{party.id}",
        {
            "type": "join_request_update",
            "action": action,
            "pending_count": party.join_requests.filter(status=PartyJoinRequest.Status.PENDING).count(),
            "request": {
                "id": join_request.id,
                "user_id": join_request.user_id,
                "nickname": _display_name(join_request.user),
                "status": join_request.status,
            },
        },
    )


def _broadcast_join_request_result(party, join_request):
    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        f"chat_{party.id}",
        {
            "type": "join_request_result",
            "target_user_id": join_request.user_id,
            "status": join_request.status,
            "message": "참가 신청이 수락되었습니다." if join_request.status == PartyJoinRequest.Status.APPROVED else "참가 신청이 거절되었습니다.",
        },
    )


def _broadcast_join_request_result_custom(party, user_id, status, message):
    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        f"chat_{party.id}",
        {
            "type": "join_request_result",
            "target_user_id": user_id,
            "status": status,
            "message": message,
        },
    )


def _pinned_notice_payload(party):
    if not party.pinned_message_id:
        return None

    pinned = ChatMessage.objects.select_related("user").filter(pk=party.pinned_message_id, party=party).first()
    if not pinned:
        return None

    if pinned.user:
        sender_name = pinned.sender_name or _display_name(pinned.user)
    else:
        sender_name = pinned.sender_name or "시스템"
    return {
        "message_id": pinned.id,
        "content": pinned.content,
        "sender": sender_name,
    }


def _broadcast_pinned_notice_update(party):
    channel_layer = get_channel_layer()
    payload = _pinned_notice_payload(party)
    async_to_sync(channel_layer.group_send)(
        f"chat_{party.id}",
        {
            "type": "pinned_notice_update",
            "pinned": payload,
        },
    )


def _promote_waitlist_entries(party):
    promoted_users = []

    with transaction.atomic():
        locked_party = get_object_or_404(Party.objects.select_for_update(), pk=party.pk)
        while locked_party.status != Party.Status.CLOSED and locked_party.current_member_count < locked_party.max_members:
            entry = locked_party.waitlist_entries.select_related("user").order_by("queued_at").first()
            if not entry:
                break

            target_user = entry.user

            if BlackList.objects.filter(party=locked_party, user=target_user).exists():
                entry.delete()
                continue

            if PartyMember.objects.filter(party=locked_party, user=target_user, is_active=True).exists():
                entry.delete()
                continue

            membership = PartyMember.objects.filter(party=locked_party, user=target_user).first()
            if membership:
                membership.is_active = True
                membership.save(update_fields=["is_active"])
            else:
                PartyMember.objects.create(party=locked_party, user=target_user, is_active=True)

            promoted_users.append({"id": target_user.id, "name": _display_name(target_user)})
            entry.delete()

            locked_party.refresh_from_db(fields=["current_member_count", "max_members", "status"])

    party.refresh_from_db()

    if promoted_users:
        channel_layer = get_channel_layer()
        for promoted_user in promoted_users:
            async_to_sync(channel_layer.group_send)(
                f"chat_{party.id}",
                {
                    "type": "system_message",
                    "message": f"⏫ {promoted_user['name']}님이 대기열에서 자동 입장했습니다.",
                },
            )
            _broadcast_join_request_result_custom(
                party,
                promoted_user["id"],
                "APPROVED",
                "대기열에서 자동 입장되었습니다.",
            )

    _broadcast_waitlist_update(party)


class PartyListView(LoginRequiredMixin, ListView):
    model = Party
    template_name = "parties/party_list.html"
    context_object_name = "parties"

    def get_queryset(self):
        return Party.objects.exclude(status=Party.Status.CLOSED).order_by("-created_at")


class PartyCreateView(LoginRequiredMixin, VerifiedEmailRequiredMixin, CreateView):
    model = Party
    form_class = PartyForm
    template_name = "parties/party_create.html"

    def form_valid(self, form):
        user = self.request.user
        active_party = Party.objects.filter(host=user).exclude(status=Party.Status.CLOSED).exists()

        if active_party:
            form.add_error(None, "이미 모집 중인 파티가 있습니다.")
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.host = user
            self.object = form.save()
            PartyMember.objects.create(party=self.object, user=user, is_active=True)

        return redirect("party_detail", pk=self.object.pk)


class PartyDetailView(LoginRequiredMixin, VerifiedEmailRequiredMixin, NotInBlackListMixin, DetailView):
    model = Party
    template_name = "parties/party_detail.html"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        party = self.object

        active_members = party.members.filter(is_active=True).select_related("user")
        waitlist_entries = list(party.waitlist_entries.select_related("user").order_by("queued_at"))

        context["active_members"] = active_members
        context["chat_messages"] = party.messages.select_related("user").order_by("created_at")[:50]
        context["join_policy_approval"] = party.join_policy == Party.JoinPolicy.APPROVAL
        context["waitlist_count"] = len(waitlist_entries)
        context["pinned_notice"] = _pinned_notice_payload(party)

        if user.is_authenticated:
            context["is_member"] = active_members.filter(user=user).exists()
            context["is_host"] = party.host_id == user.id
            context["my_join_request_status"] = (
                party.join_requests.filter(user=user).order_by("-requested_at").values_list("status", flat=True).first() or ""
            )
            context["my_waitlist_rank"] = _waitlist_rank(party, user.id)

            if context["is_host"]:
                context["pending_requests"] = party.join_requests.filter(
                    status=PartyJoinRequest.Status.PENDING
                ).select_related("user")
            else:
                context["pending_requests"] = []
            context["waitlist_entries"] = waitlist_entries
        else:
            context["is_member"] = False
            context["is_host"] = False
            context["my_join_request_status"] = ""
            context["my_waitlist_rank"] = None
            context["pending_requests"] = []
            context["waitlist_entries"] = waitlist_entries

        return context


class PartyJoinView(LoginRequiredMixin, VerifiedEmailRequiredMixin, NotInBlackListMixin, View):
    def post(self, request, pk):
        party = get_object_or_404(Party, pk=pk)

        if party.status == Party.Status.CLOSED:
            return redirect("party_list")

        membership = PartyMember.objects.filter(party=party, user=request.user).first()
        if membership and membership.is_active:
            return redirect("party_detail", pk=pk)

        if party.join_policy == Party.JoinPolicy.APPROVAL:
            if PartyWaitlist.objects.filter(party=party, user=request.user).exists():
                rank = _waitlist_rank(party, request.user.id) or 0
                return redirect(f"/parties/{pk}/?waitlisted=1&rank={rank}")

            join_request, created = PartyJoinRequest.objects.get_or_create(
                party=party,
                user=request.user,
                defaults={"status": PartyJoinRequest.Status.PENDING},
            )

            was_pending = join_request.status == PartyJoinRequest.Status.PENDING
            if join_request.status != PartyJoinRequest.Status.PENDING:
                join_request.status = PartyJoinRequest.Status.PENDING
                join_request.decided_at = None
                join_request.decided_by = None
                join_request.save(update_fields=["status", "decided_at", "decided_by"])
            if created or not was_pending:
                _broadcast_join_request_update(party, "created", join_request)
            return redirect(f"/parties/{pk}/?requested=1")

        if party.current_member_count < party.max_members:
            if membership and not membership.is_active:
                membership.is_active = True
                membership.save(update_fields=["is_active"])
            else:
                PartyMember.objects.update_or_create(
                    party=party,
                    user=request.user,
                    defaults={"is_active": True},
                )

            PartyJoinRequest.objects.filter(
                party=party,
                user=request.user,
                status=PartyJoinRequest.Status.PENDING,
            ).update(
                status=PartyJoinRequest.Status.CANCELLED,
                decided_at=timezone.now(),
                decided_by=party.host,
            )

            deleted, _ = PartyWaitlist.objects.filter(party=party, user=request.user).delete()
            if deleted:
                _broadcast_waitlist_update(party)

            return redirect("party_detail", pk=pk)

        PartyWaitlist.objects.get_or_create(party=party, user=request.user)
        _broadcast_waitlist_update(party)

        rank = _waitlist_rank(party, request.user.id) or 0
        return redirect(f"/parties/{pk}/?waitlisted=1&rank={rank}")


class PartyLeaveView(LoginRequiredMixin, VerifiedEmailRequiredMixin, View):
    def post(self, request, pk):
        party = get_object_or_404(Party, pk=pk)
        membership_changed = False

        if party.host == request.user:
            membership = PartyMember.objects.filter(party=party, user=request.user).first()
            if membership:
                membership.is_active = False
                membership.save()
                membership_changed = True
            else:
                party.status = Party.Status.CLOSED
                party.save()
                party.members.all().delete()
                party.messages.all().delete()
                party.blacklist.all().delete()
        else:
            membership = PartyMember.objects.filter(party=party, user=request.user).first()
            if membership and membership.is_active:
                membership.is_active = False
                membership.save()
                membership_changed = True

        deleted, _ = PartyWaitlist.objects.filter(party=party, user=request.user).delete()
        if deleted:
            _broadcast_waitlist_update(party)

        if membership_changed:
            party.refresh_from_db()
            if party.status != Party.Status.CLOSED:
                _promote_waitlist_entries(party)

        return redirect("party_list")


class KickMemberView(LoginRequiredMixin, VerifiedEmailRequiredMixin, View):
    def post(self, request, party_id, user_id):
        party = get_object_or_404(Party, pk=party_id)

        if party.host_id != request.user.id:
            return redirect("party_detail", pk=party_id)

        party_member = get_object_or_404(PartyMember, party=party, user_id=user_id)
        kicked_user_name = _display_name(party_member.user)

        party_member.is_active = False
        party_member._kicked = True
        party_member.save()

        BlackList.objects.get_or_create(party=party, user=party_member.user)
        PartyWaitlist.objects.filter(party=party, user_id=user_id).delete()

        party.refresh_from_db()
        if party.status != Party.Status.CLOSED:
            _promote_waitlist_entries(party)

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{party.id}",
            {
                "type": "user_kicked",
                "kicked_user_id": user_id,
                "kicked_user_name": kicked_user_name,
            },
        )

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "kicked_user_name": kicked_user_name})

        return redirect(f"/parties/{party_id}/?kicked_user_name={quote(kicked_user_name)}")


class TransferHostView(LoginRequiredMixin, VerifiedEmailRequiredMixin, View):
    def post(self, request, party_id, user_id):
        with transaction.atomic():
            party = get_object_or_404(Party.objects.select_for_update(), pk=party_id)
            if party.host_id != request.user.id:
                return redirect("party_detail", pk=party_id)

            target_member = PartyMember.objects.select_related("user").filter(
                party=party,
                user_id=user_id,
                is_active=True,
            ).first()

            if not target_member or target_member.user_id == party.host_id:
                return redirect("party_detail", pk=party_id)

            party.host = target_member.user
            party.save(update_fields=["host"])

        transferred_user_name = _display_name(target_member.user)
        _broadcast_member_snapshot(party)

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{party.id}",
            {
                "type": "system_message",
                "message": f"👑 {transferred_user_name}님이 새로운 방장이 되었습니다.",
                "code": "host_transferred",
                "actor_user_id": request.user.id,
            },
        )

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "transferred_user_name": transferred_user_name})

        return redirect(f"/parties/{party_id}/?host_transferred_name={quote(transferred_user_name)}")


class PartySettingsUpdateView(LoginRequiredMixin, VerifiedEmailRequiredMixin, View):
    def post(self, request, party_id):
        party = get_object_or_404(Party, pk=party_id)
        if party.host_id != request.user.id:
            return redirect("party_detail", pk=party_id)

        mode = (request.POST.get("mode") or "").strip()
        description = (request.POST.get("description") or "").strip()
        mic_required = request.POST.get("mic_required") in {"on", "1", "true", "True"}
        max_members_raw = (request.POST.get("max_members") or "").strip()

        errors = []
        if not mode:
            errors.append("모드를 입력해주세요.")
        if len(mode) > 50:
            errors.append("모드는 50자 이하로 입력해주세요.")

        try:
            max_members = int(max_members_raw)
        except ValueError:
            max_members = None
            errors.append("최대 인원은 숫자로 입력해주세요.")

        if max_members is not None and (max_members < 2 or max_members > 20):
            errors.append("최대 인원은 2~20 사이여야 합니다.")

        if errors:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"ok": False, "errors": errors}, status=400)
            return redirect(f"/parties/{party_id}/?settings_failed=1")

        changed_labels = []
        changed_max = False

        with transaction.atomic():
            locked_party = get_object_or_404(Party.objects.select_for_update(), pk=party_id)
            if locked_party.host_id != request.user.id:
                return redirect("party_detail", pk=party_id)

            if max_members < locked_party.current_member_count:
                msg = "현재 참여 인원보다 최대 인원을 작게 설정할 수 없습니다."
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({"ok": False, "errors": [msg]}, status=400)
                return redirect(f"/parties/{party_id}/?settings_failed=1")

            update_fields = []

            if locked_party.mode != mode:
                locked_party.mode = mode
                update_fields.append("mode")
                changed_labels.append("모드")

            if locked_party.description != description:
                locked_party.description = description
                update_fields.append("description")
                changed_labels.append("설명")

            if locked_party.mic_required != mic_required:
                locked_party.mic_required = mic_required
                update_fields.append("mic_required")
                changed_labels.append("마이크 필수")

            if locked_party.max_members != max_members:
                locked_party.max_members = max_members
                update_fields.append("max_members")
                changed_labels.append("최대 인원")
                changed_max = True

            if locked_party.status != Party.Status.CLOSED:
                new_status = Party.Status.FULL if locked_party.current_member_count >= locked_party.max_members else Party.Status.OPEN
                if locked_party.status != new_status:
                    locked_party.status = new_status
                    update_fields.append("status")

            if update_fields:
                locked_party.save(update_fields=update_fields)

        party.refresh_from_db()

        if changed_labels:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"chat_{party.id}",
                {
                    "type": "system_message",
                    "message": f"⚙️ 파티 설정이 변경되었습니다. ({', '.join(changed_labels)})",
                    "code": "party_settings_updated",
                    "actor_user_id": request.user.id,
                },
            )

        if changed_max and party.status != Party.Status.CLOSED:
            _promote_waitlist_entries(party)

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "ok": True,
                    "party": {
                        "mode": party.mode,
                        "description": party.description,
                        "mic_required": party.mic_required,
                        "max_members": party.max_members,
                        "current_count": party.current_member_count,
                        "status": party.get_status_display(),
                    },
                }
            )

        return redirect(f"/parties/{party_id}/?settings_updated=1")


class CancelJoinRequestView(LoginRequiredMixin, VerifiedEmailRequiredMixin, View):
    def post(self, request, pk):
        with transaction.atomic():
            party = get_object_or_404(Party.objects.select_for_update(), pk=pk)

            join_request = PartyJoinRequest.objects.select_for_update().select_related("user").filter(
                party=party,
                user=request.user,
                status=PartyJoinRequest.Status.PENDING,
            ).first()

            if not join_request:
                return redirect("party_detail", pk=pk)

            join_request.status = PartyJoinRequest.Status.CANCELLED
            join_request.decided_at = timezone.now()
            join_request.decided_by = request.user
            join_request.save(update_fields=["status", "decided_at", "decided_by"])

        _broadcast_join_request_update(party, "cancelled", join_request)
        _broadcast_join_request_result_custom(
            party,
            request.user.id,
            "CANCELLED",
            "참가 신청을 취소했습니다.",
        )
        return redirect(f"/parties/{pk}/?request_cancelled=1")


class PinNoticeView(LoginRequiredMixin, VerifiedEmailRequiredMixin, View):
    def post(self, request, party_id, message_id):
        with transaction.atomic():
            party = get_object_or_404(Party.objects.select_for_update(), pk=party_id)
            if party.host_id != request.user.id:
                return JsonResponse({"ok": False, "error": "권한이 없습니다."}, status=403)

            message = get_object_or_404(ChatMessage, pk=message_id, party=party)
            party.pinned_message = message
            party.pinned_updated_at = timezone.now()
            party.save(update_fields=["pinned_message", "pinned_updated_at"])

        _broadcast_pinned_notice_update(party)

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "pinned": _pinned_notice_payload(party)})
        return redirect("party_detail", pk=party_id)


class UnpinNoticeView(LoginRequiredMixin, VerifiedEmailRequiredMixin, View):
    def post(self, request, party_id):
        with transaction.atomic():
            party = get_object_or_404(Party.objects.select_for_update(), pk=party_id)
            if party.host_id != request.user.id:
                return JsonResponse({"ok": False, "error": "권한이 없습니다."}, status=403)

            party.pinned_message = None
            party.pinned_updated_at = timezone.now()
            party.save(update_fields=["pinned_message", "pinned_updated_at"])

        _broadcast_pinned_notice_update(party)

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "pinned": None})
        return redirect("party_detail", pk=party_id)


class ApproveJoinRequestView(LoginRequiredMixin, VerifiedEmailRequiredMixin, View):
    def post(self, request, party_id, request_id):
        with transaction.atomic():
            party = get_object_or_404(Party.objects.select_for_update(), pk=party_id)
            if party.host_id != request.user.id:
                return redirect("party_detail", pk=party_id)

            join_request = get_object_or_404(
                PartyJoinRequest.objects.select_for_update().select_related("user"),
                pk=request_id,
                party=party,
            )

            if join_request.status != PartyJoinRequest.Status.PENDING:
                return redirect("party_detail", pk=party_id)

            if party.current_member_count >= party.max_members:
                join_request.status = PartyJoinRequest.Status.APPROVED
                join_request.decided_at = timezone.now()
                join_request.decided_by = request.user
                join_request.save(update_fields=["status", "decided_at", "decided_by"])

                PartyWaitlist.objects.get_or_create(party=party, user=join_request.user)

                _broadcast_join_request_update(party, "queued", join_request)
                _broadcast_waitlist_update(party)
                rank = _waitlist_rank(party, join_request.user_id) or 0
                _broadcast_join_request_result_custom(
                    party,
                    join_request.user_id,
                    "WAITLISTED",
                    f"정원이 가득 차 대기열 {rank}번으로 이동되었습니다.",
                )
                return redirect(f"/parties/{party_id}/?moved_waitlist=1")

            join_request.status = PartyJoinRequest.Status.APPROVED
            join_request.decided_at = timezone.now()
            join_request.decided_by = request.user
            join_request.save(update_fields=["status", "decided_at", "decided_by"])

            PartyMember.objects.update_or_create(
                party=party,
                user=join_request.user,
                defaults={"is_active": True},
            )

            PartyWaitlist.objects.filter(party=party, user=join_request.user).delete()

        _broadcast_join_request_update(party, "approved", join_request)
        _broadcast_join_request_result(party, join_request)
        _broadcast_waitlist_update(party)
        return redirect("party_detail", pk=party_id)


class RejectJoinRequestView(LoginRequiredMixin, VerifiedEmailRequiredMixin, View):
    def post(self, request, party_id, request_id):
        party = get_object_or_404(Party, pk=party_id)
        if party.host_id != request.user.id:
            return redirect("party_detail", pk=party_id)

        join_request = get_object_or_404(
            PartyJoinRequest.objects.select_related("user"),
            pk=request_id,
            party=party,
        )

        if join_request.status == PartyJoinRequest.Status.PENDING:
            join_request.status = PartyJoinRequest.Status.REJECTED
            join_request.decided_at = timezone.now()
            join_request.decided_by = request.user
            join_request.save(update_fields=["status", "decided_at", "decided_by"])

            _broadcast_join_request_update(party, "rejected", join_request)
            _broadcast_join_request_result(party, join_request)

        return redirect("party_detail", pk=party_id)
