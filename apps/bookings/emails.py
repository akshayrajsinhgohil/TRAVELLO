"""Booking notification emails."""

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def send_booking_confirmation(booking):
    context = {"booking": booking, "site_name": settings.SITE_NAME, "site_url": settings.SITE_URL}
    html = render_to_string("emails/booking_confirmation.html", context)
    message = EmailMultiAlternatives(
        subject=f"You're going to {booking.package.destination.name} — {booking.reference}",
        body=strip_tags(html),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[booking.email],
    )
    message.attach_alternative(html, "text/html")
    message.send(fail_silently=True)
