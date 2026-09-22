"""Transactional email helpers for the accounts app."""

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_encode


def send_verification_email(user, request=None):
    """Send the 'confirm your email' message with a signed, expiring link."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    path = reverse("accounts:verify_email", kwargs={"uidb64": uid, "token": token})
    verify_url = f"{settings.SITE_URL}{path}"

    context = {
        "user": user,
        "verify_url": verify_url,
        "site_name": settings.SITE_NAME,
    }
    html = render_to_string("emails/verify_email.html", context)
    message = EmailMultiAlternatives(
        subject=f"Confirm your email to start booking with {settings.SITE_NAME}",
        body=strip_tags(html),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    message.attach_alternative(html, "text/html")
    message.send(fail_silently=True)
    return verify_url
