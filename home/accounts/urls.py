from django.contrib.auth.views import PasswordChangeDoneView
from django.urls import path

from .views import (
    CustomPasswordChangeView,
    LoginView,
    LogoutView,
    ProfileView,
    UserCreateView,
    UserListView,
    UserUpdateView,
)


urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("password/", CustomPasswordChangeView.as_view(), name="password_change"),
    path(
        "password/done/",
        PasswordChangeDoneView.as_view(template_name="registration/password_change_done.html"),
        name="password_change_done",
    ),
    # مدیریت کاربران — فقط مدیر
    path("users/", UserListView.as_view(), name="user-list"),
    path("users/new/", UserCreateView.as_view(), name="user-create"),
    path("users/<int:pk>/edit/", UserUpdateView.as_view(), name="user-edit"),
]
