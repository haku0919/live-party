from django.views.generic import ListView, CreateView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from .mixins import NotInBlackListMixin
from accounts.mixins import VerifiedEmailRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.db import transaction
from urllib.parse import quote
from .models import Party, PartyMember, BlackList
from .forms import PartyForm
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# 모집 중/마감 파티 목록을 보여주는 뷰입니다.
class PartyListView(LoginRequiredMixin, ListView):
    model = Party
    template_name = 'parties/party_list.html'
    context_object_name = 'parties'
    
    def get_queryset(self):
        # 종료된 방은 목록에서 숨깁니다.
        return Party.objects.exclude(status=Party.Status.CLOSED).order_by('-created_at')

    # 파티 생성 요청을 처리하는 뷰입니다.
    # 생성 성공 시 방장을 첫 활성 멤버로 자동 등록합니다.
class PartyCreateView(LoginRequiredMixin, VerifiedEmailRequiredMixin, CreateView):
    model = Party
    form_class = PartyForm
    template_name = 'parties/party_create.html'

    def form_valid(self, form):
        user = self.request.user
        # 동시에 여러 파티를 운영하지 못하도록 가드
        active_party = Party.objects.filter(host=user).exclude(status=Party.Status.CLOSED).exists()

        if active_party:
            form.add_error(None, "이미 모집 중인 파티가 있습니다.")
            return self.form_invalid(form)

        # 파티 생성 + 멤버 생성을 한 트랜잭션으로 묶어 정합성을 보장
        with transaction.atomic():
            form.instance.host = user
            self.object = form.save()
            PartyMember.objects.create(party=self.object, user=user, is_active=True)

        return redirect('party_detail', pk=self.object.pk)

# 파티 상세 화면을 렌더링하는 뷰입니다.
# URL 직접 접근 시 비활성 멤버를 재활성화(재입장)하는 정책을 포함합니다.
class PartyDetailView(LoginRequiredMixin, VerifiedEmailRequiredMixin, NotInBlackListMixin, DetailView):
    model = Party
    template_name = 'parties/party_detail.html'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        if request.user.is_authenticated:
            member = PartyMember.objects.filter(party=self.object, user=request.user).first()
            is_blacklisted = BlackList.objects.filter(party=self.object, user=request.user).exists()
            # 블랙리스트가 아니고, 기존 멤버 레코드가 비활성이면 재참여 처리
            if member and not member.is_active and not is_blacklisted:
                if self.object.status != Party.Status.CLOSED:
                    member.is_active = True
                    member.save()

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        party = self.object

        # WebSocket 연결 전 첫 렌더에 필요한 멤버 목록/권한 상태를 제공합니다.
        context['active_members'] = party.members.filter(is_active=True).select_related('user')

        if user.is_authenticated:
            context['is_member'] = party.members.filter(user=user, is_active=True).exists()
            context['is_host'] = (party.host == user)
            # 초기 채팅 로딩은 최신 50개로 제한(화면 성능)
            context['chat_messages'] = party.messages.select_related('user').order_by('created_at')[:50]
        else:
            context['is_member'] = False
            context['is_host'] = False
        return context

# 파티 참여/재참여 요청을 처리하는 뷰입니다.
class PartyJoinView(LoginRequiredMixin, VerifiedEmailRequiredMixin, NotInBlackListMixin, View):
    def post(self, request, pk):
        party = get_object_or_404(Party, pk=pk)

        if party.status == Party.Status.CLOSED:
            return redirect('party_list')

        # 기존 레코드가 있으면 is_active를 true로 복구하고,
        # 없으면 새 멤버 레코드를 생성합니다.
        if party.current_member_count < party.max_members:
            PartyMember.objects.update_or_create(
                party=party,
                user=request.user,
                defaults={'is_active': True}
            )
        
        return redirect('party_detail', pk=pk)

# 파티 나가기 요청을 처리하는 뷰입니다.
# 방장이 나가면 시그널에서 새 방장 위임/종료 여부를 처리합니다.
class PartyLeaveView(LoginRequiredMixin, VerifiedEmailRequiredMixin, View):
    def post(self, request, pk):
        party = get_object_or_404(Party, pk=pk)

        if party.host == request.user:
            membership = PartyMember.objects.filter(party=party, user=request.user).first()
            if membership:
                # 방장도 일반 멤버처럼 비활성화만 처리하고,
                # 실제 위임/종료는 signals.handle_member_change가 담당
                membership.is_active = False
                membership.save()
            else:
                # 예외적으로 멤버 레코드가 없으면 안전하게 종료 처리
                party.status = Party.Status.CLOSED
                party.save()
        else:
            membership = PartyMember.objects.filter(party=party, user=request.user).first()
            if membership:
                membership.is_active = False
                membership.save()

        return redirect('party_list')

# 방장의 강퇴 요청을 처리하는 뷰입니다.
class KickMemberView(LoginRequiredMixin, VerifiedEmailRequiredMixin, View):
    def post(self, request, party_id, user_id):
        party = get_object_or_404(Party, pk=party_id)

        if party.host != request.user:
            return redirect('party_detail', pk=party_id)

        partyMember = get_object_or_404(PartyMember, party=party, user_id=user_id)
        kicked_user_name = partyMember.user.nickname or partyMember.user.username
        # _kicked 플래그로 시그널에서 "일반 퇴장 메시지"를 생략하게 만듭니다.
        partyMember.is_active = False
        partyMember._kicked = True
        partyMember.save()

        # 재입장 차단용 블랙리스트 기록
        BlackList.objects.get_or_create(party=party, user=partyMember.user)


        channel_layer = get_channel_layer()
        # 채팅방 참가자에게 강퇴 이벤트 브로드캐스트
        async_to_sync(channel_layer.group_send)(
            f"chat_{party.id}",
            {
                "type": "user_kicked",
                "kicked_user_id": user_id,
                "kicked_user_name": kicked_user_name
            }
        )

        # 비동기 강퇴(현재 화면 유지) 요청이면 JSON으로 응답
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "kicked_user_name": kicked_user_name})

        # 폼 POST 직접 호출일 때는 상세 페이지로 복귀
        return redirect(f"/parties/{party_id}/?kicked_user_name={quote(kicked_user_name)}")