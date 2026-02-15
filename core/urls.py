from django.contrib import admin
from django.urls import path, include
from .views import MainView
from django.views.generic import TemplateView

# core 앱의 기본 페이지 라우팅입니다.
urlpatterns = [
    path('', MainView.as_view(), name='main'),
    path('guide/', TemplateView.as_view(template_name='core/guide.html'), name='guide'),
]