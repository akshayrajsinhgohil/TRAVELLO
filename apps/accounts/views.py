"""Account views: registration, email verification, dashboard, wishlist."""

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Count, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.http import require_POST
from django.views.generic import FormView, TemplateView, UpdateView

from apps.bookings.models import Booking
from apps.destinations.models import Package
from apps.reviews.models import Review

from .emails import send_verification_email
from .forms import LoginForm, ProfileForm, RegistrationForm
from .models import Wishlist

User = get_user_model()


class RegisterView(FormView):
    template_name = "accounts/register.html"
    form_class = RegistrationForm
    success_url = reverse_lazy("accounts:dashboard")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("accounts:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        send_verification_email(user, self.request)
        login(self.request, user, backend="apps.accounts.backends.EmailOrUsernameBackend")
        messages.success(
            self.request,
            "Account created. Check your inbox for the confirmation link.",
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["meta_title"] = "Create your Travello account"
        return context


class TravelloLoginView(LoginView):
    template_name = "accounts/login.html"
    form_class = LoginForm
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["meta_title"] = "Sign in to Travello"
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Welcome back, {self.request.user.display_name}.")
        return response


class TravelloLogoutView(LogoutView):
    """Logout that also accepts GET so the nav link works without a form."""

    http_method_names = ["get", "post", "options"]

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)


def verify_email(request, uidb64, token):
    """Confirm an email address from the signed link sent at registration."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if not user.is_email_verified:
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified"])
        messages.success(request, "Email confirmed. You can book trips now.")
        return redirect("accounts:dashboard")

    messages.error(
        request,
        "That confirmation link has expired. Send yourself a fresh one below.",
    )
    return render(request, "accounts/verify_failed.html", status=400)


@login_required
@require_POST
def resend_verification(request):
    if request.user.is_email_verified:
        messages.info(request, "Your email is already confirmed.")
    else:
        send_verification_email(request.user, request)
        messages.success(request, f"New link sent to {request.user.email}.")
    return redirect("accounts:dashboard")


class DashboardView(LoginRequiredMixin, TemplateView):
    """The traveller's own dashboard: trips, spend, saved trips, reviews."""

    template_name = "accounts/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        bookings = (
            Booking.objects.filter(user=user)
            .select_related("package", "package__destination")
            .order_by("-created_at")
        )
        context.update(
            {
                "meta_title": "Your trips",
                "bookings": bookings[:6],
                "booking_count": bookings.count(),
                "upcoming": bookings.upcoming().first(),
                "total_spent": bookings.paid().aggregate(t=Sum("total_amount"))["t"] or 0,
                "countries": bookings.paid()
                .values("package__destination__country")
                .distinct()
                .count(),
                "wishlist": Wishlist.objects.filter(user=user).select_related(
                    "package", "package__destination"
                )[:4],
                "reviews": Review.objects.filter(user=user).select_related("package")[:3],
            }
        )
        return context


class ProfileView(LoginRequiredMixin, UpdateView):
    template_name = "accounts/profile.html"
    form_class = ProfileForm
    success_url = reverse_lazy("accounts:profile")

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Profile saved.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["meta_title"] = "Your profile"
        return context


class WishlistView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/wishlist.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["meta_title"] = "Saved trips"
        context["saved"] = (
            Wishlist.objects.filter(user=self.request.user)
            .select_related("package", "package__destination")
            .annotate(review_count=Count("package__reviews"))
        )
        return context


@login_required
@require_POST
def toggle_wishlist(request, slug):
    """Save or unsave a trip. Answers JSON for the inline heart button."""
    package = get_object_or_404(Package, slug=slug, is_active=True)
    entry = Wishlist.objects.filter(user=request.user, package=package).first()
    if entry:
        entry.delete()
        saved = False
    else:
        Wishlist.objects.create(user=request.user, package=package)
        saved = True

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"saved": saved, "package": package.slug})

    messages.success(request, "Trip saved." if saved else "Removed from saved trips.")
    return redirect(package.get_absolute_url())
