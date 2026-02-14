from django.views.generic import ListView, CreateView, DetailView, View
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from accounts.mixins import VerifiedEmailRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.db import transaction
from .models import Party, PartyMember
from .forms import PartyForm
from chat.models import ChatMessage 

# 1. 파티 목록
class PartyListView(LoginRequiredMixin, ListView):
    model = Party
    template_name = 'parties/party_list.html'
    context_object_name = 'parties'
    
    def get_queryset(self):
        return Party.objects.exclude(status=Party.Status.CLOSED).order_by('-created_at')

# 2. 파티 생성
class PartyCreateView(LoginRequiredMixin, VerifiedEmailRequiredMixin, CreateView):
    model = Party
    form_class = PartyForm
    template_name = 'parties/party_create.html'

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

        return redirect('party_detail', pk=self.object.pk)

# 3. 파티 상세 (✅ 여기가 수정되었습니다!)
class PartyDetailView(LoginRequiredMixin, VerifiedEmailRequiredMixin, DetailView):
    model = Party
    template_name = 'parties/party_detail.html'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        # 나갔던 사람이 다시 URL로 들어왔을 때 '참여 중'으로 복구하는 로직
        if request.user.is_authenticated:
            member = PartyMember.objects.filter(party=self.object, user=request.user).first()
            if member and not member.is_active:
                if self.object.status != Party.Status.CLOSED:
                    member.is_active = True
                    member.save() # 이때 시그널이 울려서 '재입장 알림'이 감

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        party = self.object

        # ✅ [추가됨] 화면이 열리자마자 멤버 명단을 보여주기 위한 데이터
        # 이 코드가 있어야 들어오자마자 리스트가 뜹니다!
        context['active_members'] = party.members.filter(is_active=True).select_related('user')

        if user.is_authenticated:
            context['is_member'] = party.members.filter(user=user, is_active=True).exists()
            context['is_host'] = (party.host == user)
            # 채팅 내역 50개 가져오기
            context['chat_messages'] = party.messages.select_related('user').order_by('created_at')[:50]
        else:
            context['is_member'] = False
            context['is_host'] = False
        return context

# 4. 파티 참여 (재입장 로직은 여기서만 처리)
class PartyJoinView(LoginRequiredMixin, VerifiedEmailRequiredMixin, View):
    def post(self, request, pk):
        party = get_object_or_404(Party, pk=pk)
        
        if party.status == Party.Status.CLOSED:
            return redirect('party_list')

        # ✅ update_or_create: 없으면 만들고, 있으면(나갔던 사람이면) is_active=True로 수정
        if party.current_member_count < party.max_members:
            PartyMember.objects.update_or_create(
                party=party,
                user=request.user,
                defaults={'is_active': True}
            )
        
        return redirect('party_detail', pk=pk)

# 5. 파티 나가기
class PartyLeaveView(LoginRequiredMixin, VerifiedEmailRequiredMixin, View):
    def post(self, request, pk):
        party = get_object_or_404(Party, pk=pk)
        
        if party.host == request.user:
            party.status = Party.Status.CLOSED
            party.save()
        else:
            # 나갈 때는 is_active = False 처리
            membership = PartyMember.objects.filter(party=party, user=request.user).first()
            if membership:
                membership.is_active = False
                membership.save()
                
        return redirect('party_list')