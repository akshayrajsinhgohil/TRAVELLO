from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api_views import DestinationViewSet, PackageViewSet, globe_pins

router = DefaultRouter()
router.register("destinations", DestinationViewSet, basename="api-destination")
router.register("trips", PackageViewSet, basename="api-package")

urlpatterns = [
    path("", include(router.urls)),
    path("globe-pins/", globe_pins, name="api-globe-pins"),
]
