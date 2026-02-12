from django.urls import path
from .views import ProfileView  # 작성한 뷰 임포트

urlpatterns = [
    path("profile/", ProfileView.as_view(), name="profile"),
]