"""Read-only API serializers — useful for a future mobile app or JS widgets."""

from rest_framework import serializers

from .models import Category, Destination, Package


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "emoji", "description")


class DestinationSerializer(serializers.ModelSerializer):
    url = serializers.CharField(source="get_absolute_url", read_only=True)
    image = serializers.CharField(source="display_image", read_only=True)

    class Meta:
        model = Destination
        fields = (
            "id", "name", "slug", "country", "region", "tagline",
            "latitude", "longitude", "image", "url", "is_featured",
        )


class PackageSerializer(serializers.ModelSerializer):
    destination = DestinationSerializer(read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    url = serializers.CharField(source="get_absolute_url", read_only=True)
    image = serializers.CharField(source="display_image", read_only=True)
    current_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    rating = serializers.FloatField(source="average_rating", read_only=True)

    class Meta:
        model = Package
        fields = (
            "id", "title", "slug", "summary", "price", "discount_price",
            "current_price", "duration_days", "duration_nights", "max_guests",
            "difficulty", "image", "url", "rating", "destination", "categories",
        )
