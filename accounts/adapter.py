from allauth.account.adapter import DefaultAccountAdapter

# 회원가입 폼의 커스텀 필드를 User 모델로 반영하는 어댑터
class CustomAccountAdapter(DefaultAccountAdapter):
    # 회원가입 시 추가 사용자 필드를 채운 뒤 저장함.
    def save_user(self, request, user, form, commit=True):
        # cleaned_data는 CustomSignupForm에서 검증이 끝난 입력값임.
        data = form.cleaned_data

        user.nickname = data.get('nickname')
        user.phone = data.get('phone')
        user.birth_year = data.get('birth_year')
        user.gender = data.get('gender')
        user.mic_enabled = data.get('mic_enabled')

        user = super().save_user(request, user, form, commit=False)

        # commit=False 후 수동 저장하면 필드 주입 순서를 더 명확히 통제할 수 있음.
        if commit:
            user.save()

        return user