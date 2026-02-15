from django.urls import path
from . import views

# HTTP 라우팅(SSR 페이지/폼 POST)입니다.
# 실시간 이벤트(WebSocket)는 parties/routing.py에서 별도로 정의합니다.
urlpatterns = [
    path('parties/', views.PartyListView.as_view(), name='party_list'),
    path('parties/create/', views.PartyCreateView.as_view(), name='party_create'),
    path('parties/<int:pk>/', views.PartyDetailView.as_view(), name='party_detail'),
    path('parties/<int:pk>/join/', views.PartyJoinView.as_view(), name='party_join'),
    path('parties/<int:pk>/leave/', views.PartyLeaveView.as_view(), name='party_leave'),
    path('parties/<int:party_id>/members/<int:user_id>/kick/', views.KickMemberView.as_view(), name='party_kick'),
]