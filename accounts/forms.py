import datetime
from django import forms
from django.core.exceptions import ValidationError
from allauth.account.forms import SignupForm
from .models import User, Game
from allauth.account.models import EmailAddress

# 회원가입 입력값 검증과 사용자 생성 후 추가 필드 저장을 처리하는 폼
class CustomSignupForm(SignupForm):
    # allauth 기본 필드에 프로젝트 커스텀 필드를 추가함.
    username = forms.CharField(max_length=150, label="아이디(username)")
    nickname = forms.CharField(max_length=15, label="닉네임")
    phone = forms.CharField(max_length=15, label="전화번호")
    gender = forms.ChoiceField(choices=User.Gender.choices, label="성별")
    
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

    # 출생년도 유효성을 검증함.
    def clean_birth_year(self):
        birth_year = self.cleaned_data['birth_year']
        current_year = datetime.date.today().year
        
        if birth_year > current_year:
            raise ValidationError("미래의 연도는 입력할 수 없습니다.")
            
        if birth_year < (current_year - 100):
            raise ValidationError("올바른 출생년도를 입력해주세요.")

        if birth_year > (current_year - 14):
            raise ValidationError("만 14세 이상만 가입할 수 있습니다.")

        return birth_year

    # 닉네임 중복 여부를 검증함.
    def clean_nickname(self):
        nickname = self.cleaned_data['nickname']
        if User.objects.filter(nickname=nickname).exists():
            raise ValidationError("이미 사용 중인 닉네임입니다.")
        return nickname

    # 전화번호 중복 여부를 검증함.
    def clean_phone(self):
        phone = self.cleaned_data['phone']
        if User.objects.filter(phone=phone).exists():
            raise ValidationError("이미 가입된 전화번호입니다.")
        return phone

    # 회원가입 사용자 생성 후 다중선택 게임 정보를 저장함.
    def save(self, request):
        # 실제 User 생성은 allauth + accounts.adapter.CustomAccountAdapter가 담당함.
        user = super().save(request)
        # ManyToMany는 객체 생성 후에만 set() 가능
        user.main_games.set(self.cleaned_data["main_games"])
        
        return user

# 프로필 수정 시 허용 필드와 닉네임 중복 검증을 처리하는 폼
class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['nickname', 'mic_enabled', 'main_games']
        
        labels = {
            'nickname': '닉네임',
            'mic_enabled': '마이크 사용 여부',
            'main_games': '주로 하는 게임 (다중 선택)',
        }
        
        widgets = {
            'nickname': forms.TextInput(attrs={
                'class': 'podo-input',
                'placeholder': '변경할 닉네임을 입력하세요',
                'style': 'width: 100%; padding: 12px; border-radius: 12px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: white;'
            }),
            'mic_enabled': forms.CheckboxInput(attrs={
                'id': 'mic_toggle', 
                'class': 'mic-checkbox-input' 
            }),
            'main_games': forms.CheckboxSelectMultiple(),
        }

    # 본인 계정을 제외한 닉네임 중복 여부를 검증함.
    def clean_nickname(self):
        nickname = self.cleaned_data.get('nickname')
        
        if User.objects.filter(nickname=nickname).exclude(pk=self.instance.pk).exists():
            raise ValidationError("이미 사용 중인 닉네임입니다. 다른 걸 써주세요!")
            
        return nickname

# 이메일 변경 시 신규 이메일 유효성을 검증하는 폼
class EmailChangeForm(forms.Form):
    email = forms.EmailField(
        label="새로운 이메일",
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': '변경할 이메일 주소를 입력하세요',
            'style': 'width: 100%; padding: 12px; border-radius: 8px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: white;'
        })
    )

    def clean_email(self):
        email = self.cleaned_data['email']
        # allauth의 EmailAddress 테이블 기준으로 전역 중복을 막음.
        if EmailAddress.objects.filter(email=email).exists():
            raise forms.ValidationError("이미 등록된 이메일입니다. 다른 이메일을 사용해주세요.")
        return email