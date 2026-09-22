from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.TravelloLoginView.as_view(), name="login"),
    path("logout/", views.TravelloLogoutView.as_view(), name="logout"),
    path("verify/<uidb64>/<token>/", views.verify_email, name="verify_email"),
    path("verify/resend/", views.resend_verification, name="resend_verification"),
    path("me/", views.DashboardView.as_view(), name="dashboard"),
    path("me/profile/", views.ProfileView.as_view(), name="profile"),
    path("me/saved/", views.WishlistView.as_view(), name="wishlist"),
    path("saved/<slug:slug>/toggle/", views.toggle_wishlist, name="toggle_wishlist"),

    # Password reset flow (Django's built-in views with Travello templates)
    path(
        "password/reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            email_template_name="registration/password_reset_email.html",
            success_url="/accounts/password/reset/sent/",
        ),
        name="password_reset",
    ),
    path(
        "password/reset/sent/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "password/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
            success_url="/accounts/password/reset/complete/",
        ),
        name="password_reset_confirm",
    ),
    path(
        "password/reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]
