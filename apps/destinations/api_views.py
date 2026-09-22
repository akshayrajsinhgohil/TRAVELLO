from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Destination, Package
from .serializers import DestinationSerializer, PackageSerializer


class DestinationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Destination.objects.published()
    serializer_class = DestinationSerializer
    lookup_field = "slug"


class PackageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Package.objects.published().select_related("destination")
    serializer_class = PackageSerializer
    lookup_field = "slug"

    def get_queryset(self):
        qs = super().get_queryset()
        term = self.request.query_params.get("q")
        if term:
            qs = qs.filter(title__icontains=term)
        return qs


@api_view(["GET"])
def globe_pins(request):
    """Coordinates for the 3D globe on the landing page."""
    points = (
        Destination.objects.published()
        .exclude(latitude__isnull=True)
        .exclude(longitude__isnull=True)
        .values("name", "country", "slug", "latitude", "longitude", "is_featured")
    )
    return Response(list(points))
