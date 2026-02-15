from django.contrib import messages
from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.urls import reverse

# 파티 접근 전에 블랙리스트 여부를 공통 검사하는 믹스인입니다.
# 적용 대상 예: PartyDetailView, PartyJoinView
class NotInBlackListMixin(AccessMixin):
    # dispatch는 HTTP 메서드(get/post) 실행 전에 공통 전처리를 넣기 좋은 지점입니다.
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        # URL 패턴에 따라 pk 또는 party_id를 파티 식별자로 사용
        party_id = kwargs.get("party_id") or kwargs.get("pk")

        if not user.is_authenticated:
            return self.handle_no_permission()

        if party_id and user.blacklisted_in_parties.filter(party_id=party_id).exists():
            messages.error(request, "죄송합니다. 이 파티에 접근할 수 없습니다.")
            # query param은 party_list 템플릿에서 모달 표시 트리거로 사용
            return redirect(f"{reverse('party_list')}?blocked=1")

        return super().dispatch(request, *args, **kwargs)