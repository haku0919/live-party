from django.urls import path

from . import views

urlpatterns = [
    path("parties/", views.PartyListView.as_view(), name="party_list"),
    path("parties/create/", views.PartyCreateView.as_view(), name="party_create"),
    path("parties/<int:pk>/", views.PartyDetailView.as_view(), name="party_detail"),
    path("parties/<int:pk>/join/", views.PartyJoinView.as_view(), name="party_join"),
    path("parties/<int:pk>/join/cancel/", views.CancelJoinRequestView.as_view(), name="party_join_request_cancel"),
    path("parties/<int:pk>/leave/", views.PartyLeaveView.as_view(), name="party_leave"),
    path("parties/<int:party_id>/settings/", views.PartySettingsUpdateView.as_view(), name="party_settings_update"),
    path("parties/<int:party_id>/members/<int:user_id>/kick/", views.KickMemberView.as_view(), name="party_kick"),
    path("parties/<int:party_id>/members/<int:user_id>/transfer-host/", views.TransferHostView.as_view(), name="party_transfer_host"),
    path("parties/<int:party_id>/pin/<int:message_id>/", views.PinNoticeView.as_view(), name="party_pin_notice"),
    path("parties/<int:party_id>/pin/clear/", views.UnpinNoticeView.as_view(), name="party_unpin_notice"),
    path("parties/<int:party_id>/join-requests/<int:request_id>/approve/", views.ApproveJoinRequestView.as_view(), name="party_join_request_approve"),
    path("parties/<int:party_id>/join-requests/<int:request_id>/reject/", views.RejectJoinRequestView.as_view(), name="party_join_request_reject"),
]
