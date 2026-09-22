"""Checkout, payment and booking management views."""

import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from apps.destinations.models import Package

from .emails import send_booking_confirmation
from .forms import BookingForm
from .gateways import get_gateway
from .models import Booking, Coupon, Payment


@login_required
def checkout(request, slug):
    """Step 1 — collect dates, guests and contact details, then price the trip."""
    package = get_object_or_404(Package.objects.select_related("destination"), slug=slug, is_active=True)

    if request.method == "POST":
        form = BookingForm(request.POST, package=package, user=request.user)
        if form.is_valid():
            coupon = form.get_coupon()
            guests = form.cleaned_data["adults"] + form.cleaned_data["children"]
            pricing = package.quote(guests=guests, coupon=coupon)

            with transaction.atomic():
                booking = form.save(commit=False)
                booking.user = request.user
                booking.package = package
                booking.coupon = coupon
                booking.unit_price = pricing["unit_price"]
                booking.base_amount = pricing["base_amount"]
                booking.discount_amount = pricing["discount_amount"]
                booking.tax_amount = pricing["tax_amount"]
                booking.total_amount = pricing["total_amount"]
                booking.save()

            return redirect("bookings:pay", reference=booking.reference)
    else:
        form = BookingForm(package=package, user=request.user)

    return render(
        request,
        "bookings/checkout.html",
        {
            "package": package,
            "form": form,
            "quote": package.quote(guests=2),
            "meta_title": f"Book {package.title}",
        },
    )


@login_required
def price_quote(request, slug):
    """Live price recalculation for the checkout summary (called on change)."""
    package = get_object_or_404(Package, slug=slug, is_active=True)
    guests = request.GET.get("guests", 1)
    code = (request.GET.get("coupon") or "").strip().upper()
    coupon = Coupon.objects.filter(code=code).first() if code else None
    if coupon and not coupon.is_valid:
        coupon = None

    quote = package.quote(guests=guests, coupon=coupon)
    return JsonResponse(
        {key: str(value) for key, value in quote.items()}
        | {"coupon_applied": bool(coupon), "coupon_code": coupon.code if coupon else ""}
    )


@login_required
def pay(request, reference):
    """Step 2 — hand the booking to the configured payment gateway."""
    booking = get_object_or_404(Booking, reference=reference, user=request.user)
    if booking.payment_status == Booking.PAYMENT_PAID:
        return redirect("bookings:confirmation", reference=booking.reference)

    gateway = get_gateway()
    order = gateway.create_order(booking)

    Payment.objects.create(
        booking=booking,
        gateway=order["gateway"],
        order_id=order["order_id"],
        amount=booking.total_amount,
        currency=order.get("currency", "INR"),
        raw_response=order,
    )

    return render(
        request,
        "bookings/pay.html",
        {
            "booking": booking,
            "order": order,
            "order_json": json.dumps(order),
            "meta_title": f"Pay for {booking.reference}",
        },
    )


@login_required
@require_POST
def payment_callback(request, reference):
    """Step 3 — verify the gateway response and confirm the booking."""
    booking = get_object_or_404(Booking, reference=reference, user=request.user)
    payload = {
        "order_id": request.POST.get("order_id", ""),
        "payment_id": request.POST.get("payment_id", ""),
        "signature": request.POST.get("signature", ""),
    }

    gateway = get_gateway()
    payment = booking.payments.filter(order_id=payload["order_id"]).first()

    if gateway.verify(payload):
        booking.mark_paid()
        if payment:
            payment.payment_id = payload["payment_id"]
            payment.signature = payload["signature"]
            payment.status = Payment.STATUS_SUCCESS
            payment.save(update_fields=["payment_id", "signature", "status"])
        send_booking_confirmation(booking)
        messages.success(request, f"Payment received. {booking.reference} is confirmed.")
        return redirect("bookings:confirmation", reference=booking.reference)

    if payment:
        payment.status = Payment.STATUS_FAILED
        payment.save(update_fields=["status"])
    booking.payment_status = Booking.PAYMENT_FAILED
    booking.save(update_fields=["payment_status"])
    messages.error(
        request,
        "We couldn't verify that payment. Nothing was charged — try again below.",
    )
    return redirect("bookings:pay", reference=booking.reference)


class BookingConfirmationView(LoginRequiredMixin, DetailView):
    model = Booking
    template_name = "bookings/confirmation.html"
    context_object_name = "booking"
    slug_field = "reference"
    slug_url_kwarg = "reference"

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).select_related(
            "package", "package__destination"
        )


class BookingListView(LoginRequiredMixin, ListView):
    template_name = "bookings/booking_list.html"
    context_object_name = "bookings"
    paginate_by = 10

    def get_queryset(self):
        qs = Booking.objects.filter(user=self.request.user).select_related(
            "package", "package__destination"
        )
        self.tab = self.request.GET.get("show", "all")
        if self.tab == "upcoming":
            qs = qs.upcoming()
        elif self.tab == "past":
            qs = qs.past()
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tab"] = self.tab
        context["meta_title"] = "Your bookings"
        return context


class BookingDetailView(LoginRequiredMixin, DetailView):
    model = Booking
    template_name = "bookings/booking_detail.html"
    context_object_name = "booking"
    slug_field = "reference"
    slug_url_kwarg = "reference"

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).select_related(
            "package", "package__destination"
        ).prefetch_related("payments", "package__itinerary")


@login_required
@require_POST
def cancel_booking(request, reference):
    booking = get_object_or_404(Booking, reference=reference, user=request.user)
    if not booking.is_cancellable:
        messages.error(
            request,
            "This booking can no longer be cancelled online. Contact support and "
            "we'll sort it out.",
        )
        return redirect(booking.get_absolute_url())

    booking.status = Booking.STATUS_CANCELLED
    booking.cancellation_reason = request.POST.get("reason", "")[:500]
    if booking.payment_status == Booking.PAYMENT_PAID:
        booking.payment_status = Booking.PAYMENT_REFUNDED
        message = f"{booking.reference} cancelled. Your refund lands in 5–7 working days."
    else:
        message = f"{booking.reference} cancelled."
    booking.save(update_fields=["status", "payment_status", "cancellation_reason", "updated_at"])
    messages.success(request, message)
    return redirect("bookings:list")
