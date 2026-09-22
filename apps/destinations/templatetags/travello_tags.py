"""Small display helpers used across Travello templates."""

from django import template
from django.conf import settings

register = template.Library()


@register.filter
def money(value):
    """Format a number as currency: 24999 -> ₹24,999"""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return value
    if amount == int(amount):
        return f"{settings.CURRENCY_SYMBOL}{int(amount):,}"
    return f"{settings.CURRENCY_SYMBOL}{amount:,.2f}"


@register.filter
def stars(value):
    """Render a 0–5 rating as filled and empty stars."""
    try:
        filled = int(round(float(value)))
    except (TypeError, ValueError):
        filled = 0
    filled = max(0, min(5, filled))
    return "★" * filled + "☆" * (5 - filled)


@register.simple_tag(takes_context=True)
def query_replace(context, **kwargs):
    """Rebuild the querystring with some params replaced — used by pagination."""
    params = context["request"].GET.copy()
    for key, value in kwargs.items():
        if value in (None, ""):
            params.pop(key, None)
        else:
            params[key] = value
    return params.urlencode()


@register.filter
def initials_of(user):
    return getattr(user, "initials", "??")
