from django.views.generic import ListView, CreateView, DetailView, View
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.db import transaction
from .models import Party, PartyMember
from .forms import PartyForm

# 1. 파티 목록
class PartyListView(ListView):
    model = Party
    template_name = 'parties/party_list.html'
    context_object_name = 'parties'
    
    def get_queryset(self):
        return Party.objects.exclude(status=Party.Status.CLOSED).order_by('-created_at')

# 2. 파티 생성
class PartyCreateView(LoginRequiredMixin, CreateView):
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

        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('party_detail', kwargs={'pk': self.object.pk})

# 3. 파티 상세 (입장 처리 포함)
class PartyDetailView(DetailView):
    model = Party
    template_name = 'parties/party_detail.html'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        # [자동 부활] 로그인 유저가 과거 멤버였다면 상태를 True로 복구
        if request.user.is_authenticated:
            member = PartyMember.objects.filter(party=self.object, user=request.user).first()
            if member and not member.is_active:
                # 단, 파티가 종료되지 않았을 때만 부활
                if self.object.status != Party.Status.CLOSED:
                    member.is_active = True
                    member.save()

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_authenticated:
            context['is_member'] = self.object.members.filter(user=user, is_active=True).exists()
            # ✅ [추가] 현재 접속자가 방장인지 여부 전달
            context['is_host'] = (self.object.host == user)
        else:
            context['is_member'] = False
            context['is_host'] = False
        return context

# 4. 파티 참여
class PartyJoinView(LoginRequiredMixin, View):
    def post(self, request, pk):
        party = get_object_or_404(Party, pk=pk)
        
        if party.status == Party.Status.CLOSED:
            return redirect('party_list')

        if party.current_member_count < party.max_members:
            PartyMember.objects.update_or_create(
                party=party,
                user=request.user,
                defaults={'is_active': True}
            )
        
        return redirect('party_detail', pk=pk)

# 5. 파티 나가기 (소프트 딜리트)
class PartyLeaveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        party = get_object_or_404(Party, pk=pk)
        
        if party.host == request.user:
            # 호스트 -> 파티 종료 (여기서 리다이렉트 되므로 JS 알림 불필요)
            party.status = Party.Status.CLOSED
            party.save()
        else:
            # 멤버 -> 비활성화 (기록 남김)
            membership = PartyMember.objects.filter(party=party, user=request.user).first()
            if membership:
                membership.is_active = False
                membership.save()
                
        return redirect('party_list')