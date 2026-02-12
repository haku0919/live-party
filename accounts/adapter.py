# accounts/adapter.py
from allauth.account.adapter import DefaultAccountAdapter

class CustomAccountAdapter(DefaultAccountAdapter):

    def save_user(self, request, user, form, commit=True):
        # 1. 부모 클래스의 save_user를 부르기 전에 데이터를 먼저 채워줍니다.
        data = form.cleaned_data
        
        user.nickname = data.get('nickname')
        user.phone = data.get('phone')
        user.birth_year = data.get('birth_year')
        user.gender = data.get('gender')
        user.mic_enabled = data.get('mic_enabled')
        
        # 2. 이제 저장을 시도합니다. (데이터가 채워졌으니 에러 안 남!)
        user = super().save_user(request, user, form, commit=False)
        
        if commit:
            user.save()
            
        return user