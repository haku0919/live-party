import datetime  # 날짜 계산용
from django import forms
from django.core.exceptions import ValidationError
from allauth.account.forms import SignupForm
from .models import User, Game

class CustomSignupForm(SignupForm):
    # 1. 입력 필드 정의
    username = forms.CharField(max_length=150, label="아이디(username)")
    nickname = forms.CharField(max_length=15, label="닉네임")
    phone = forms.CharField(max_length=15, label="전화번호")
    gender = forms.ChoiceField(choices=User.Gender.choices, label="성별")
    
    # 숫자 입력칸 (화살표 제거 CSS 적용됨)
    birth_year = forms.IntegerField(
        label="출생년도",
        widget=forms.NumberInput(attrs={'placeholder': '예: 2002'})
    )
    
    main_games = forms.ModelMultipleChoiceField(
        queryset=Game.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="주로 하는 게임",
    )

    mic_enabled = forms.BooleanField(
        required=False, 
        label="마이크 사용 여부",
        widget=forms.CheckboxInput(attrs={'class': 'checkbox-input'})
    )

    # -------------------------------------------
    # 2. 유효성 검사 (Clean Methods)
    # -------------------------------------------

    # [생년 검사] 미래, 너무 과거, 14세 미만 차단
    def clean_birth_year(self):
        birth_year = self.cleaned_data['birth_year']
        current_year = datetime.date.today().year
        
        if birth_year > current_year:
            raise ValidationError("미래의 연도는 입력할 수 없습니다.")
            
        if birth_year < (current_year - 100):
            raise ValidationError("올바른 출생년도를 입력해주세요.")

        # 만 14세 미만 가입 제한 (필요 없으면 이 부분 삭제하세요)
        if birth_year > (current_year - 14):
            raise ValidationError("만 14세 이상만 가입할 수 있습니다.")

        return birth_year

    # [닉네임 중복 검사]
    def clean_nickname(self):
        nickname = self.cleaned_data['nickname']
        if User.objects.filter(nickname=nickname).exists():
            raise ValidationError("이미 사용 중인 닉네임입니다.")
        return nickname

    # [전화번호 중복 검사]
    def clean_phone(self):
        phone = self.cleaned_data['phone']
        if User.objects.filter(phone=phone).exists():
            raise ValidationError("이미 가입된 전화번호입니다.")
        return phone

    # -------------------------------------------
    # 3. 저장 로직 (Save)
    # -------------------------------------------
    def save(self, request):
        # 1. super().save()가 실행될 때, 아까 만든 'Adapter'가 작동해서
        # nickname, phone, birth_year 등을 미리 다 넣어줍니다.
        user = super().save(request) 

        # 2. ManyToMany 필드(게임 목록)는 유저가 생성된 '후'에 넣어야 하므로 여기서 합니다.
        user.main_games.set(self.cleaned_data["main_games"])
        
        return user