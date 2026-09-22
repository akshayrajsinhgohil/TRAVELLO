from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from apps.bookings.models import Booking
from apps.destinations.models import Package

from .forms import ReviewForm
from .models import Review


@login_required
@require_POST
def submit_review(request, slug):
    """Post a review for a trip. One per traveller per trip."""
    package = get_object_or_404(Package, slug=slug, is_active=True)

    if Review.objects.filter(package=package, user=request.user).exists():
        messages.info(request, "You've already reviewed this trip.")
        return redirect(package.get_absolute_url())

    form = ReviewForm(request.POST)
    if not form.is_valid():
        first_error = next(iter(form.errors.values()))[0]
        messages.error(request, first_error)
        return redirect(f"{package.get_absolute_url()}#write-review")

    review = form.save(commit=False)
    review.user = request.user
    review.package = package
    # Link to a completed booking so the review shows a "verified trip" badge.
    review.booking = (
        Booking.objects.filter(user=request.user, package=package)
        .paid()
        .order_by("-start_date")
        .first()
    )
    review.save()
    messages.success(
        request,
        "Thanks — your review is with our team and goes live once it's checked.",
    )
    return redirect(package.get_absolute_url())


@login_required
@require_POST
def delete_review(request, pk):
    review = get_object_or_404(Review, pk=pk, user=request.user)
    package_url = review.package.get_absolute_url()
    review.delete()
    messages.success(request, "Review deleted.")
    return redirect(package_url)
