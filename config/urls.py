"""Root URL configuration.

URLs are deliberately short and readable for SEO:
    /destinations/goa/           -> destination detail
    /trips/backwaters-and-beaches/ -> package detail
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from apps.core.sitemaps import SITEMAPS

admin.site.site_header = "Travello control room"
admin.site.site_title = "Travello admin"
admin.site.index_title = "What would you like to manage?"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls", namespace="core")),
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    path("", include("apps.destinations.urls", namespace="destinations")),
    path("bookings/", include("apps.bookings.urls", namespace="bookings")),
    path("reviews/", include("apps.reviews.urls", namespace="reviews")),
    path("staff/", include("apps.dashboard.urls", namespace="dashboard")),
    path("api/", include("apps.destinations.api_urls")),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="sitemap"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "apps.core.views.handler404"
handler500 = "apps.core.views.handler500"
