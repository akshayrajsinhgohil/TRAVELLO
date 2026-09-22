"""Sitemaps so search engines find every destination and trip."""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from apps.destinations.models import Destination, Package


class StaticSitemap(Sitemap):
    priority = 0.7
    changefreq = "weekly"

    def items(self):
        return ["core:home", "core:about", "core:contact",
                "destinations:destination_list", "destinations:package_list"]

    def location(self, item):
        return reverse(item)


class DestinationSitemap(Sitemap):
    priority = 0.8
    changefreq = "weekly"

    def items(self):
        return Destination.objects.published()

    def lastmod(self, obj):
        return obj.updated_at


class PackageSitemap(Sitemap):
    priority = 0.9
    changefreq = "daily"

    def items(self):
        return Package.objects.published()

    def lastmod(self, obj):
        return obj.updated_at


SITEMAPS = {
    "static": StaticSitemap,
    "destinations": DestinationSitemap,
    "trips": PackageSitemap,
}
