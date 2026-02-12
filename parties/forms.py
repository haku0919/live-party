# parties/forms.py
from django import forms
from .models import Party

class PartyForm(forms.ModelForm):
    class Meta:
        model = Party
        fields = ['game', 'mode', 'title', 'description', 'max_members']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': '파티 제목을 입력해주세요 (예: 랭크 듀오 구함)',
                'style': 'width: 100%; padding: 12px; background: rgba(255,255,255,0.05); border: 1px solid var(--border); border-radius: 10px; color: white;'
            }),
            'description': forms.Textarea(attrs={
                'placeholder': '내용을 입력해주세요',
                'rows': 4,
                'style': 'width: 100%; padding: 12px; background: rgba(255,255,255,0.05); border: 1px solid var(--border); border-radius: 10px; color: white;'
            }),
            # ✅ 여기가 핵심: HTML 태그에 min="2", max="20" 속성을 심어줍니다.
            'max_members': forms.NumberInput(attrs={
                'min': 2,
                'max': 20,
                'style': 'width: 100%; padding: 12px; background: rgba(255,255,255,0.05); border: 1px solid var(--border); border-radius: 10px; color: white;'
            }),
            # 나머지 필드들도 스타일 통일
            'game': forms.Select(attrs={'style': 'width: 100%; padding: 12px; background: rgba(255,255,255,0.05); border: 1px solid var(--border); border-radius: 10px; color: white;'}),
            'mode': forms.Select(attrs={'style': 'width: 100%; padding: 12px; background: rgba(255,255,255,0.05); border: 1px solid var(--border); border-radius: 10px; color: white;'}),
        }