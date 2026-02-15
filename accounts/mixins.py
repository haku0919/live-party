from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.contrib import messages
from allauth.account.models import EmailAddress

# 이메일 인증 완료 사용자만 접근을 허용하는 믹스인
class VerifiedEmailRequiredMixin(AccessMixin):
    # 미인증 사용자를 메인으로 리다이렉트합니다.
    def dispatch(self, request, *args, **kwargs):
        # LoginRequiredMixin보다 앞뒤 MRO에 따라 이 코드가 먼저 실행될 수 있어,
        # 비로그인 처리도 방어적으로 포함합니다.
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not EmailAddress.objects.filter(user=request.user, verified=True).exists():
            messages.error(request, "이메일 인증을 완료해야 파티를 생성할 수 있습니다 📧")
            return redirect('main')

        return super().dispatch(request, *args, **kwargs)