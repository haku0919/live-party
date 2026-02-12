from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from parties.models import PartyMember

class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "account/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # ✅ [핵심 로직] 내가 참여했던 파티 5개 가져오기
        # select_related로 DB 성능 최적화 (파티+게임 정보 한방에 로딩)
        # order_by('-joined_at')으로 '최근 참여한 순서'대로 정렬
        context['recent_matches'] = PartyMember.objects.filter(user=self.request.user) \
                                    .select_related('party__game') \
                                    .order_by('-joined_at')[:5]
        
        return context