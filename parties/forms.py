from django import forms
from .models import Party

# 파티 생성/수정 입력값과 위젯 스타일을 정의하는 폼
class PartyForm(forms.ModelForm):
    class Meta:
        model = Party
        fields = ['game', 'mode', 'description', 'max_members', 'mic_required', 'join_policy']
        widgets = {
            'game': forms.Select(attrs={
                'class': 'input',
            }),
            'mode': forms.TextInput(attrs={
                'placeholder': '예: 랭크, 일반, 칼바람, 신속, 내전',
                'class': 'input',
            }),
            'description': forms.Textarea(attrs={
                'placeholder': '내용을 입력하세요', 
                'rows': 3,
                'class': 'input',
            }),
            'max_members': forms.NumberInput(attrs={
                'class': 'input',
                'min': 2,
                'max': 20,
            }),
            'mic_required': forms.CheckboxInput(attrs={
                'id': 'mic_checkbox',
            }),
            'join_policy': forms.Select(attrs={
                'class': 'input',
            }),
        }
        labels = {
            'game': '게임 선택',
            'mode': '게임 모드',
            'description': '내용',
            'max_members': '최대 인원',
            'mic_required': '마이크 필수 여부',
            'join_policy': '입장 방식',
        }
