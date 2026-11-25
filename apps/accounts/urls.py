from django.contrib.auth import views as auth_views
from django.urls import path

from apps.accounts import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.ClayLoginView.as_view(), name="login"),
    path("logout/", views.ClayLogoutView.as_view(), name="logout"),
    path(
        "password-reset/",
        views.ClayPasswordResetView.as_view(),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "password-reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(template_name="accounts/password_reset_confirm.html"),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(template_name="accounts/password_reset_complete.html"),
        name="password_reset_complete",
    ),
    path("profile/", views.profile, name="profile"),
    path("profile/<int:pk>/", views.profile, name="profile_detail"),
    path("team/", views.team_list, name="team_list"),
    path("team/create/", views.team_create, name="team_create"),
    path("team/<int:pk>/toggle-active/", views.team_toggle_active, name="team_toggle_active"),
]
