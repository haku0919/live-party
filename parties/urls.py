from django.urls import path
from . import views

urlpatterns = [
    path('parties/', views.PartyListView.as_view(), name='party_list'),
    path('parties/create/', views.PartyCreateView.as_view(), name='party_create'),
    path('parties/<int:pk>/', views.PartyDetailView.as_view(), name='party_detail'),
    path('parties/<int:pk>/join/', views.PartyJoinView.as_view(), name='party_join'),
    path('parties/<int:pk>/leave/', views.PartyLeaveView.as_view(), name='party_leave'),
]