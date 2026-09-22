"""Landing page, static pages, contact form and newsletter signup."""

from django.contrib import messages
from django.db.models import Count, Min, Q
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from apps.destinations.models import Category, Destination, Package
from apps.reviews.models import Review

from .forms import ContactForm, NewsletterForm
from .models import NewsletterSubscriber, Testimonial


class HomeView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        featured_destinations = (
            Destination.objects.featured()
            .with_trip_stats()
            .annotate(from_price=Min("packages__price", filter=Q(packages__is_active=True)))[:6]
        )
        context.update(
            {
                "meta_title": "Travello — trips worth the time off",
                "meta_description": (
                    "Hand-built trips across beaches, mountains and old cities. "
                    "Real itineraries, honest prices, reviews from people who went."
                ),
                "destinations": featured_destinations,
                "featured_trips": (
                    Package.objects.featured()
                    .select_related("destination")
                    .with_ratings()[:6]
                ),
                "categories": Category.objects.annotate(
                    total=Count("packages", filter=Q(packages__is_active=True))
                ).filter(total__gt=0)[:8],
                "testimonials": Testimonial.objects.filter(is_active=True)[:6],
                "stats": {
                    "destinations": Destination.objects.published().count(),
                    "trips": Package.objects.published().count(),
                    "reviews": Review.objects.filter(is_approved=True).count(),
                },
                "newsletter_form": NewsletterForm(),
            }
        )
        return context


class AboutView(TemplateView):
    template_name = "core/about.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["meta_title"] = "About Travello"
        context["meta_description"] = (
            "Why Travello exists, how trips get picked, and who builds them."
        )
        return context


def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request, "Message received. Someone replies within one working day."
            )
            return redirect("core:contact")
    else:
        initial = {}
        if request.user.is_authenticated:
            initial = {
                "name": request.user.get_full_name() or request.user.username,
                "email": request.user.email,
                "phone": request.user.phone,
            }
        form = ContactForm(initial=initial)

    return render(
        request,
        "core/contact.html",
        {
            "form": form,
            "meta_title": "Contact Travello",
            "meta_description": "Questions about a booking or a trip? Talk to a human.",
        },
    )


@require_POST
def newsletter_signup(request):
    form = NewsletterForm(request.POST)
    if form.is_valid():
        email = form.cleaned_data["email"]
        _, created = NewsletterSubscriber.objects.get_or_create(
            email=email, defaults={"source": request.POST.get("source", "footer")}
        )
        messages.success(
            request,
            "You're on the list." if created else "You're already on the list.",
        )
    else:
        messages.error(request, "That email doesn't look right. Try again?")
    return redirect(request.META.get("HTTP_REFERER", "core:home"))


def handler404(request, exception):
    return render(request, "404.html", status=404)


def handler500(request):
    return render(request, "500.html", status=500)
