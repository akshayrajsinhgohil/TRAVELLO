"""Staff analytics dashboard.

Read-only overview of the numbers staff ask for most: revenue, bookings,
which destinations sell, and what needs attention right now. Charts are drawn
by Chart.js from the JSON in the context.
"""

import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Avg, Count, F, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.views.generic import TemplateView

from apps.bookings.models import Booking
from apps.core.models import ContactMessage, NewsletterSubscriber
from apps.destinations.models import Destination, Package
from apps.reviews.models import Review

User = get_user_model()


class StaffOnlyMixin(UserPassesTestMixin):
    """Only staff accounts reach the dashboard; everyone else gets 403."""

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff


class DashboardView(StaffOnlyMixin, TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        month_start = today.replace(day=1)
        paid = Booking.objects.paid()

        revenue_total = paid.aggregate(t=Sum("total_amount"))["t"] or Decimal("0")
        revenue_month = paid.filter(created_at__date__gte=month_start).aggregate(
            t=Sum("total_amount")
        )["t"] or Decimal("0")

        # Trailing 12 months of revenue and booking counts.
        since = (month_start - timedelta(days=365)).replace(day=1)
        monthly = (
            paid.filter(created_at__date__gte=since)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(revenue=Sum("total_amount"), bookings=Count("id"))
            .order_by("month")
        )
        months = [row["month"].strftime("%b %y") for row in monthly]
        revenue_series = [float(row["revenue"]) for row in monthly]
        booking_series = [row["bookings"] for row in monthly]

        # Top destinations by revenue.
        top_destinations = (
            Destination.objects.annotate(
                bookings=Count("packages__bookings",
                               filter=Q(packages__bookings__payment_status="paid")),
                revenue=Sum("packages__bookings__total_amount",
                            filter=Q(packages__bookings__payment_status="paid")),
            )
            .filter(bookings__gt=0)
            .order_by("-revenue")[:6]
        )

        status_counts = list(
            Booking.objects.values("status").annotate(n=Count("id")).order_by("-n")
        )

        context.update(
            {
                "meta_title": "Travello dashboard",
                "kpis": {
                    "revenue_total": revenue_total,
                    "revenue_month": revenue_month,
                    "bookings_total": Booking.objects.count(),
                    "bookings_month": Booking.objects.filter(
                        created_at__date__gte=month_start
                    ).count(),
                    "pending": Booking.objects.filter(status="pending").count(),
                    "travellers": User.objects.filter(is_staff=False).count(),
                    "avg_order": paid.aggregate(a=Avg("total_amount"))["a"] or Decimal("0"),
                    "avg_rating": Review.objects.filter(is_approved=True).aggregate(
                        a=Avg("rating")
                    )["a"],
                },
                "needs_attention": {
                    "unapproved_reviews": Review.objects.filter(is_approved=False).count(),
                    "unresolved_messages": ContactMessage.objects.filter(
                        is_resolved=False
                    ).count(),
                    "awaiting_payment": Booking.objects.filter(
                        status="pending", payment_status="unpaid"
                    ).count(),
                    "departing_soon": Booking.objects.active()
                    .filter(start_date__range=(today, today + timedelta(days=7)))
                    .count(),
                },
                "chart_months": json.dumps(months),
                "chart_revenue": json.dumps(revenue_series),
                "chart_bookings": json.dumps(booking_series),
                "chart_status_labels": json.dumps(
                    [dict(Booking.STATUS_CHOICES)[row["status"]] for row in status_counts]
                ),
                "chart_status_values": json.dumps([row["n"] for row in status_counts]),
                "chart_destination_labels": json.dumps(
                    [d.name for d in top_destinations]
                ),
                "chart_destination_values": json.dumps(
                    [float(d.revenue or 0) for d in top_destinations]
                ),
                "top_destinations": top_destinations,
                "top_trips": (
                    Package.objects.annotate(
                        sold=Count("bookings", filter=Q(bookings__payment_status="paid")),
                        earned=Sum("bookings__total_amount",
                                   filter=Q(bookings__payment_status="paid")),
                    )
                    .filter(sold__gt=0)
                    .order_by("-sold")[:5]
                ),
                "recent_bookings": (
                    Booking.objects.select_related("user", "package", "package__destination")[:8]
                ),
                "departing_soon_list": (
                    Booking.objects.active()
                    .filter(start_date__gte=today)
                    .select_related("package", "user")
                    .order_by("start_date")[:5]
                ),
                "pending_reviews": (
                    Review.objects.filter(is_approved=False)
                    .select_related("user", "package")[:5]
                ),
                "subscriber_count": NewsletterSubscriber.objects.filter(
                    is_active=True
                ).count(),
            }
        )
        return context
