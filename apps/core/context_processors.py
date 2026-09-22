"""Values every template needs, without repeating queries in each view."""

from django.conf import settings

from apps.destinations.models import Destination


def site_context(request):
    return {
        "SITE_NAME": settings.SITE_NAME,
        "SITE_TAGLINE": settings.SITE_TAGLINE,
        "SITE_URL": settings.SITE_URL,
        "CURRENCY_SYMBOL": settings.CURRENCY_SYMBOL,
        "nav_destinations": Destination.objects.published().order_by("name")[:6],
    }
