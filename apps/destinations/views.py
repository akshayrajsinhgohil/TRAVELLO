"""Browsing views: destination index, destination detail, trip list & detail."""

from django.db.models import Avg, Count, Min, Prefetch, Q
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView, ListView

from apps.accounts.models import Wishlist
from apps.reviews.forms import ReviewForm
from apps.reviews.models import Review

from .forms import TripFilterForm
from .models import Category, Destination, Package


class DestinationListView(ListView):
    """All destinations, with a live count of bookable trips."""

    model = Destination
    template_name = "destinations/destination_list.html"
    context_object_name = "destinations"
    paginate_by = 12

    def get_queryset(self):
        qs = Destination.objects.published().with_trip_stats().annotate(
            from_price=Min("packages__price", filter=Q(packages__is_active=True))
        )
        query = self.request.GET.get("q", "").strip()
        if query:
            qs = qs.filter(
                Q(name__icontains=query)
                | Q(country__icontains=query)
                | Q(region__icontains=query)
                | Q(tagline__icontains=query)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["meta_title"] = "Every destination on Travello"
        context["meta_description"] = (
            "Browse beaches, mountains, heritage towns and road trips, "
            "with prices and real traveller ratings."
        )
        context["query"] = self.request.GET.get("q", "")
        return context


class DestinationDetailView(DetailView):
    model = Destination
    template_name = "destinations/destination_detail.html"
    context_object_name = "destination"

    def get_queryset(self):
        return Destination.objects.published().prefetch_related("gallery")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        destination = self.object
        context["packages"] = (
            destination.packages.published().with_ratings().prefetch_related("categories")
        )
        context["meta_title"] = destination.seo_title
        context["meta_description"] = destination.seo_description
        context["nearby"] = (
            Destination.objects.published()
            .filter(country=destination.country)
            .exclude(pk=destination.pk)[:3]
        )
        return context


class PackageListView(ListView):
    """Searchable, filterable trip catalogue."""

    model = Package
    template_name = "destinations/package_list.html"
    context_object_name = "packages"
    paginate_by = 9

    def get_queryset(self):
        qs = (
            Package.objects.published()
            .select_related("destination")
            .prefetch_related("categories")
            .with_ratings()
        )
        self.filter_form = TripFilterForm(self.request.GET or None)

        if not self.filter_form.is_valid():
            return qs.order_by("-is_featured", "-created_at")

        data = self.filter_form.cleaned_data

        if data.get("q"):
            term = data["q"]
            qs = qs.filter(
                Q(title__icontains=term)
                | Q(summary__icontains=term)
                | Q(description__icontains=term)
                | Q(destination__name__icontains=term)
                | Q(destination__country__icontains=term)
                | Q(categories__name__icontains=term)
            ).distinct()

        if data.get("destination"):
            qs = qs.filter(destination=data["destination"])
        if data.get("category"):
            qs = qs.filter(categories=data["category"])
        if data.get("min_price"):
            qs = qs.filter(price__gte=data["min_price"])
        if data.get("max_price"):
            qs = qs.filter(price__lte=data["max_price"])
        if data.get("guests"):
            qs = qs.filter(max_guests__gte=data["guests"])
        if data.get("start_date"):
            qs = qs.filter(
                Q(available_to__gte=data["start_date"]) | Q(available_to__isnull=True)
            )

        ordering = {
            "price_low": ("price",),
            "price_high": ("-price",),
            "rating": ("-rating_avg", "-rating_count"),
            "duration": ("duration_days",),
            "popular": ("-is_featured", "-rating_count", "-created_at"),
        }
        return qs.order_by(*ordering.get(data.get("sort") or "popular"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.filter_form
        context["categories"] = Category.objects.annotate(
            total=Count("packages", filter=Q(packages__is_active=True))
        )
        context["meta_title"] = "Find your next trip"
        context["meta_description"] = (
            "Filter trips by destination, budget, dates and travel style. "
            "Real prices, real itineraries, no guesswork."
        )
        # Keep filters when paginating.
        params = self.request.GET.copy()
        params.pop("page", None)
        context["querystring"] = params.urlencode()
        context["result_count"] = context["paginator"].count if context.get("paginator") else 0
        return context


class PackageDetailView(DetailView):
    model = Package
    template_name = "destinations/package_detail.html"
    context_object_name = "package"

    def get_queryset(self):
        return (
            Package.objects.published()
            .select_related("destination")
            .prefetch_related("gallery", "itinerary", "categories")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        package = self.object
        reviews = (
            package.reviews.filter(is_approved=True)
            .select_related("user")
            .order_by("-created_at")
        )
        context.update(
            {
                "reviews": reviews[:8],
                "review_count": reviews.count(),
                "rating_average": reviews.aggregate(a=Avg("rating"))["a"],
                "rating_breakdown": self._rating_breakdown(reviews),
                "review_form": ReviewForm(),
                "meta_title": package.seo_title,
                "meta_description": package.seo_description,
                "similar": (
                    Package.objects.published()
                    .filter(destination=package.destination)
                    .exclude(pk=package.pk)
                    .with_ratings()[:3]
                ),
                "quote": package.quote(guests=2),
            }
        )
        user = self.request.user
        if user.is_authenticated:
            context["in_wishlist"] = Wishlist.objects.filter(
                user=user, package=package
            ).exists()
            context["user_review"] = Review.objects.filter(
                user=user, package=package
            ).first()
        return context

    @staticmethod
    def _rating_breakdown(reviews):
        """Counts per star value, for the bar chart beside the reviews."""
        total = reviews.count() or 1
        counts = dict(
            reviews.values_list("rating").annotate(n=Count("rating")).order_by()
        )
        return [
            {"stars": star, "count": counts.get(star, 0),
             "percent": round(counts.get(star, 0) / total * 100)}
            for star in range(5, 0, -1)
        ]
