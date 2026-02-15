from django.shortcuts import render
from django.views import View

# 메인 랜딩 페이지를 렌더링하는 뷰
class MainView(View):
    # GET 요청에 대해 메인 템플릿을 반환합니다.
    def get(self, request):
        return render(request, 'core/main.html')

# 서비스 가이드 페이지를 렌더링하는 뷰
class GuideView(View):
    # GET 요청에 대해 가이드 템플릿을 반환합니다.
    def get(self, request):
        return render(request, 'core/guide.html')