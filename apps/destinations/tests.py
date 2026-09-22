"""Catalogue tests: browsing, search, filters, sorting and SEO helpers."""

import json
from datetime import timedelta
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.core.test_factories import make_category, make_destination, make_package, make_user
from apps.reviews.models import Review

from .models import Destination, Package


class CatalogueSetUp(TestCase):
    """A small but varied catalogue the filter tests can lean on."""

    @classmethod
    def setUpTestData(cls):
        cls.beaches = make_category("Beaches")
        cls.mountains = make_category("Mountains")

        cls.goa = make_destination("Goa", "India", is_featured=True)
        cls.ladakh = make_destination("Ladakh", "India")
        cls.bali = make_destination("Bali", "Indonesia", is_featured=True)

        cls.cheap = make_package(
            destination=cls.goa, title="Goa Beach Break", price="9000", duration_days=3,
            max_guests=4,
        )
        cls.cheap.categories.add(cls.beaches)

        cls.mid = make_package(
            destination=cls.ladakh, title="Ladakh Overland", price="52000",
            duration_days=7, max_guests=12, is_featured=True,
        )
        cls.mid.categories.add(cls.mountains)

        cls.pricey = make_package(
            destination=cls.bali, title="Bali Unfiltered", price="68900",
            duration_days=9, max_guests=14,
        )
        cls.pricey.categories.add(cls.beaches)

        cls.hidden = make_package(
            destination=cls.goa, title="Retired Trip", price="1000", is_active=False
        )


class DestinationListTests(CatalogueSetUp):
    url = reverse("destinations:destination_list")

    def test_page_lists_active_destinations(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["destinations"]), 3)

    def test_inactive_destinations_are_hidden(self):
        Destination.objects.filter(pk=self.bali.pk).update(is_active=False)

        response = self.client.get(self.url)

        names = {d.name for d in response.context["destinations"]}
        self.assertNotIn("Bali", names)

    def test_search_matches_the_country_too(self):
        response = self.client.get(self.url, {"q": "Indonesia"})

        names = [d.name for d in response.context["destinations"]]
        self.assertEqual(names, ["Bali"])

    def test_trip_counts_exclude_hidden_trips(self):
        response = self.client.get(self.url)

        goa = next(d for d in response.context["destinations"] if d.name == "Goa")
        self.assertEqual(goa.trip_count, 1)


class DestinationDetailTests(CatalogueSetUp):
    def test_detail_page_renders_its_trips(self):
        response = self.client.get(self.goa.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Goa Beach Break")
        self.assertNotContains(response, "Retired Trip")

    def test_slug_is_generated_from_name_and_country(self):
        self.assertEqual(self.bali.slug, "bali-indonesia")

    def test_nearby_suggests_the_same_country(self):
        response = self.client.get(self.goa.get_absolute_url())

        nearby = {d.name for d in response.context["nearby"]}
        self.assertEqual(nearby, {"Ladakh"})

    def test_starting_price_uses_the_cheapest_live_trip(self):
        self.assertEqual(self.goa.starting_price, Decimal("9000"))

    def test_inactive_destinations_404(self):
        Destination.objects.filter(pk=self.bali.pk).update(is_active=False)
        self.assertEqual(self.client.get(self.bali.get_absolute_url()).status_code, 404)


class PackageListFilterTests(CatalogueSetUp):
    url = reverse("destinations:package_list")

    def _titles(self, **params):
        response = self.client.get(self.url, params)
        self.assertEqual(response.status_code, 200)
        return [p.title for p in response.context["packages"]]

    def test_unfiltered_list_shows_only_live_trips(self):
        titles = self._titles()
        self.assertEqual(len(titles), 3)
        self.assertNotIn("Retired Trip", titles)

    def test_free_text_search_covers_destination_names(self):
        self.assertEqual(self._titles(q="Ladakh"), ["Ladakh Overland"])

    def test_free_text_search_covers_the_title(self):
        self.assertEqual(self._titles(q="Unfiltered"), ["Bali Unfiltered"])

    def test_filter_by_destination(self):
        self.assertEqual(self._titles(destination=self.goa.pk), ["Goa Beach Break"])

    def test_filter_by_category_slug(self):
        titles = self._titles(category="mountains")
        self.assertEqual(titles, ["Ladakh Overland"])

    def test_price_floor_and_ceiling(self):
        self.assertEqual(
            sorted(self._titles(min_price=10000, max_price=60000)), ["Ladakh Overland"]
        )

    def test_group_size_filter_excludes_small_trips(self):
        titles = self._titles(guests=10)
        self.assertNotIn("Goa Beach Break", titles)
        self.assertEqual(len(titles), 2)

    def test_departure_date_filter_respects_availability(self):
        soon = timezone.localdate() + timedelta(days=5)
        Package.objects.filter(pk=self.cheap.pk).update(available_to=soon)

        titles = self._titles(start_date=(soon + timedelta(days=30)).isoformat())

        self.assertNotIn("Goa Beach Break", titles)

    def test_sort_by_price_ascending(self):
        self.assertEqual(
            self._titles(sort="price_low"),
            ["Goa Beach Break", "Ladakh Overland", "Bali Unfiltered"],
        )

    def test_sort_by_price_descending(self):
        self.assertEqual(
            self._titles(sort="price_high"),
            ["Bali Unfiltered", "Ladakh Overland", "Goa Beach Break"],
        )

    def test_sort_by_duration(self):
        self.assertEqual(self._titles(sort="duration")[0], "Goa Beach Break")

    def test_nonsense_price_range_is_reported_not_crashed(self):
        response = self.client.get(self.url, {"min_price": 500, "max_price": 100})

        self.assertEqual(response.status_code, 200)
        self.assertIn("max_price", response.context["filter_form"].errors)

    def test_filters_survive_pagination(self):
        response = self.client.get(self.url, {"q": "Ladakh", "page": 1})
        self.assertEqual(response.status_code, 200)


class PackageDetailTests(CatalogueSetUp):
    def test_detail_page_renders(self):
        response = self.client.get(self.mid.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "destinations/package_detail.html")
        self.assertContains(response, "Ladakh Overland")

    def test_only_approved_reviews_appear(self):
        user = make_user("reviewer")
        Review.objects.create(
            package=self.mid, user=user, rating=5,
            title="Loved it", comment="A" * 40, is_approved=True,
        )
        Review.objects.create(
            package=self.mid, user=make_user("pending"), rating=1,
            title="Held back", comment="B" * 40, is_approved=False,
        )

        response = self.client.get(self.mid.get_absolute_url())

        self.assertContains(response, "Loved it")
        self.assertNotContains(response, "Held back")
        self.assertEqual(self.mid.average_rating, 5.0)
        self.assertEqual(self.mid.review_total, 1)

    def test_itinerary_days_are_ordered(self):
        days = list(self.mid.itinerary.values_list("day_number", flat=True))
        self.assertEqual(days, sorted(days))

    def test_hidden_trips_404(self):
        self.assertEqual(self.client.get(self.hidden.get_absolute_url()).status_code, 404)


class PackageModelTests(TestCase):
    def test_slug_collisions_get_a_suffix(self):
        first = make_package(title="Same Name Trip")
        second = make_package(
            destination=make_destination("Elsewhere", "Nepal"), title="Same Name Trip"
        )

        self.assertEqual(first.slug, "same-name-trip")
        self.assertEqual(second.slug, "same-name-trip-2")

    def test_multiline_text_becomes_a_list(self):
        package = make_package(
            highlights="Sunrise walk\n\n  Beach day  \nNight market"
        )
        self.assertEqual(
            package.highlight_list, ["Sunrise walk", "Beach day", "Night market"]
        )

    def test_duration_label(self):
        self.assertEqual(make_package(duration_days=5, duration_nights=4).duration_label, "5D / 4N")

    def test_seo_falls_back_when_meta_is_blank(self):
        package = make_package(title="SEO Trip", summary="A short summary.")
        self.assertIn("SEO Trip", package.seo_title)
        self.assertEqual(package.seo_description, "A short summary.")

    def test_explicit_meta_wins(self):
        package = make_package(title="Meta Trip", meta_title="Custom title")
        self.assertEqual(package.seo_title, "Custom title")


class GlobeApiTests(CatalogueSetUp):
    def test_globe_pins_returns_located_destinations(self):
        response = self.client.get("/api/globe-pins/")

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        pins = payload if isinstance(payload, list) else payload.get("results", payload)
        self.assertTrue(len(pins) >= 3)


class SeoRouteTests(CatalogueSetUp):
    def test_sitemap_lists_trips_and_destinations(self):
        response = self.client.get("/sitemap.xml")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.mid.slug)
        self.assertContains(response, self.goa.slug)

    def test_robots_txt_is_served(self):
        response = self.client.get("/robots.txt")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain")
        self.assertContains(response, "Sitemap")

    def test_urls_are_slug_based_not_id_based(self):
        self.assertIn("/trips/ladakh-overland/", self.mid.get_absolute_url())
        self.assertIn("/destinations/goa-india/", self.goa.get_absolute_url())

    def test_accented_names_still_produce_a_reversible_url(self):
        """Regression: 'Reykjavík' once kept its accent and broke reverse()."""
        destination = make_destination("Reykjavík", "Iceland")

        self.assertEqual(destination.slug, "reykjavik-iceland")
        # reverse() would raise NoReverseMatch if a non-ASCII character survived.
        self.assertEqual(
            destination.get_absolute_url(), "/destinations/reykjavik-iceland/"
        )
        self.assertEqual(self.client.get(destination.get_absolute_url()).status_code, 200)

    def test_punctuation_in_a_trip_title_is_stripped_from_the_slug(self):
        package = make_package(title="Kyoto in Autumn: Temples, Trails & Kaiseki")

        self.assertEqual(package.slug, "kyoto-in-autumn-temples-trails-kaiseki")
        self.assertEqual(self.client.get(package.get_absolute_url()).status_code, 200)


class SeedDataTests(TestCase):
    """The demo seeder has to stay runnable — it is the first thing anyone runs."""

    def test_seed_data_populates_a_browsable_catalogue(self):
        call_command("seed_data", "--no-demo-bookings", verbosity=0)

        self.assertTrue(Destination.objects.published().exists())
        self.assertTrue(Package.objects.published().exists())

        # Every seeded row must produce a URL that actually resolves.
        for destination in Destination.objects.published():
            with self.subTest(destination=destination.slug):
                response = self.client.get(destination.get_absolute_url())
                self.assertEqual(response.status_code, 200)

        for package in Package.objects.published():
            with self.subTest(package=package.slug):
                response = self.client.get(package.get_absolute_url())
                self.assertEqual(response.status_code, 200)

    def test_running_it_twice_does_not_duplicate(self):
        call_command("seed_data", "--no-demo-bookings", verbosity=0)
        first = Destination.objects.count(), Package.objects.count()

        call_command("seed_data", "--no-demo-bookings", verbosity=0)

        self.assertEqual((Destination.objects.count(), Package.objects.count()), first)
