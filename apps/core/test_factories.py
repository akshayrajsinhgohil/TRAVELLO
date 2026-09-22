"""Small builders so tests read as intent rather than boilerplate.

These are deliberately plain functions rather than a factory library — one less
dependency, and the defaults stay obvious when a test fails.
"""

import itertools
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.bookings.models import Booking, Coupon
from apps.destinations.models import Category, Destination, ItineraryDay, Package

User = get_user_model()

# Slugs, usernames and coupon codes are all unique. Rather than make every test
# invent its own names, the builders below fall back to a counter.
_counter = itertools.count(1)


def make_user(username=None, password="Tr@vello-2026", **extra):
    username = username or f"tester{next(_counter)}"
    defaults = {
        "email": f"{username}@example.com",
        "first_name": username.title(),
        "phone": "+91 9000000000",
    }
    defaults.update(extra)
    user = User.objects.create_user(username=username, password=password, **defaults)
    return user


def make_category(name=None, **extra):
    name = name or f"Category {next(_counter)}"
    return Category.objects.create(name=name, **extra)


def make_destination(name=None, country="India", **extra):
    name = name or f"Testville {next(_counter)}"
    defaults = {
        "tagline": "Sun, sand and slow mornings.",
        "description": "A long, sandy coastline with very good food.",
        "latitude": 15.2993,
        "longitude": 74.1240,
    }
    defaults.update(extra)
    return Destination.objects.create(name=name, country=country, **defaults)


def make_package(destination=None, title=None, price="10000", **extra):
    title = title or f"Test Trip {next(_counter)}"
    destination = destination or make_destination()
    defaults = {
        "summary": "A short, testable trip.",
        "description": "Everything you need and nothing you don't.",
        "price": Decimal(price),
        "duration_days": 3,
        "duration_nights": 2,
        "max_guests": 10,
        "min_guests": 1,
        "available_from": timezone.localdate(),
        "available_to": timezone.localdate() + timedelta(days=180),
    }
    defaults.update(extra)
    package = Package.objects.create(destination=destination, title=title, **defaults)
    for day in range(1, package.duration_days + 1):
        ItineraryDay.objects.create(
            package=package,
            day_number=day,
            title=f"Day {day}",
            description="Something happens.",
        )
    return package


def make_coupon(code=None, discount_type="percent", value="10", **extra):
    code = code or f"TEST{next(_counter)}"
    defaults = {
        "valid_from": timezone.localdate() - timedelta(days=1),
        "valid_to": timezone.localdate() + timedelta(days=30),
        "usage_limit": 100,
    }
    defaults.update(extra)
    return Coupon.objects.create(
        code=code, discount_type=discount_type, value=Decimal(value), **defaults
    )


def make_booking(user=None, package=None, start_in_days=30, **extra):
    """Create a booking priced through the package's own quote() method."""
    user = user or make_user()
    package = package or make_package()
    guests = extra.pop("guests", 2)
    pricing = package.quote(guests=guests, coupon=extra.pop("coupon", None))

    defaults = {
        "start_date": timezone.localdate() + timedelta(days=start_in_days),
        "adults": guests,
        "children": 0,
        "full_name": user.get_full_name() or user.username,
        "email": user.email,
        "phone": "+91 9000000000",
        "unit_price": pricing["unit_price"],
        "base_amount": pricing["base_amount"],
        "discount_amount": pricing["discount_amount"],
        "tax_amount": pricing["tax_amount"],
        "total_amount": pricing["total_amount"],
    }
    defaults.update(extra)
    return Booking.objects.create(user=user, package=package, **defaults)
