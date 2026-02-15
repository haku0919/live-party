from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from allauth.account.models import EmailAddress
from parties.models import PartyMember
from django.contrib.auth.models import User
from django.views.generic.edit import UpdateView
from .forms import ProfileUpdateForm
from django.urls import reverse_lazy
from django.contrib import messages 
from django.views.generic.edit import FormView
from .forms import EmailChangeForm
from allauth.account.models import EmailAddress, EmailConfirmation

# 프로필 페이지와 최근 참여 파티 목록을 제공하는 뷰
class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "account/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # PartyMember 역참조를 통해 최근 참여 파티 히스토리를 노출합니다.
        context['recent_matches'] = PartyMember.objects.filter(user=self.request.user) \
                                    .select_related('party__game') \
                                    .order_by('-joined_at')[:5]
        return context

# 인증 메일 재발송을 처리하는 뷰
class ResendVerificationEmailView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # allauth EmailAddress에서 "주(primary) 이메일" 레코드를 찾아 재전송합니다.
        email_obj = EmailAddress.objects.filter(user=request.user, primary=True).first()
        
        if email_obj and not email_obj.verified:
            email_obj.send_confirmation(request)
            
        return redirect('email_sent_page')

# 로그인 사용자의 프로필 수정을 처리하는 뷰
class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = ProfileUpdateForm
    template_name = 'account/profile_edit.html'
    success_url = reverse_lazy('profile')

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        # has_changed()를 쓰면 불필요한 UPDATE 쿼리를 줄일 수 있습니다.
        if not form.has_changed():
            messages.info(self.request, "변경된 내용이 없어 저장하지 않았습니다. 🤔")
            return redirect(self.success_url)
            
        messages.success(self.request, "프로필이 성공적으로 수정되었습니다! ✨")
        return super().form_valid(form)

# 이메일 변경과 인증 메일 발송을 처리하는 뷰
class EmailChangeView(LoginRequiredMixin, FormView):
    template_name = 'account/email.html'
    form_class = EmailChangeForm

    def form_valid(self, form):
        user = self.request.user
        new_email = form.cleaned_data['email']

        try:
            # 기존 EmailAddress를 비우고 새 이메일을 단일 primary로 교체합니다.
            EmailAddress.objects.filter(user=user).delete()

            new_email_obj = EmailAddress.objects.create(
                user=user,
                email=new_email,
                primary=True,
                verified=False
            )

            # User.email도 같이 맞춰야 템플릿/관리자 화면에서 값이 일관됩니다.
            user.email = new_email
            user.save()

            # allauth의 확인 토큰을 직접 발급해 인증 메일을 보냅니다.
            confirmation = EmailConfirmation.create(new_email_obj)
            confirmation.send(self.request, signup=False)

            print(f"✅ [성공] {new_email}로 인증 메일 강제 발송 완료!")

            messages.success(self.request, f"이메일이 {new_email}로 변경되었습니다! 📩 인증 메일을 꼭 확인해주세요.")
            
            return redirect('main')
            
        except Exception as e:
            print(f"❌ [오류] 이메일 변경 중 에러 발생: {e}")
            messages.error(self.request, f"오류가 발생했습니다: {str(e)}")
            return self.form_invalid(form)