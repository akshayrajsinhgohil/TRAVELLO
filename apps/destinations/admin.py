"""Admin for the catalogue, tuned for non-technical staff.

Everything a trip needs (photos, itinerary, pricing) is editable on one page
through inlines, so staff never have to hop between screens.
"""

from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from .models import (
    Category,
    Destination,
    DestinationImage,
    ItineraryDay,
    Package,
    PackageImage,
)


class ThumbnailMixin:
    @admin.display(description="Preview")
    def thumbnail(self, obj):
        url = obj.display_image
        if not url:
            return format_html('<span style="color:#888">No image yet</span>')
        return format_html(
            '<img src="{}" style="height:52px;width:78px;object-fit:cover;'
            'border-radius:8px" loading="lazy">',
            url,
        )


class DestinationImageInline(ThumbnailMixin, admin.TabularInline):
    model = DestinationImage
    extra = 1
    fields = ("thumbnail", "image", "image_url", "caption", "order")
    readonly_fields = ("thumbnail",)


class PackageImageInline(ThumbnailMixin, admin.TabularInline):
    model = PackageImage
    extra = 1
    fields = ("thumbnail", "image", "image_url", "caption", "order")
    readonly_fields = ("thumbnail",)


class ItineraryDayInline(admin.StackedInline):
    model = ItineraryDay
    extra = 1
    fields = ("day_number", "title", "description", "meals", "stay")


class PackageInline(admin.TabularInline):
    model = Package
    extra = 0
    fields = ("title", "price", "discount_price", "duration_days", "is_active")
    show_change_link = True
    can_delete = False


@admin.register(Category)
class CategoryAdmin(ThumbnailMixin, admin.ModelAdmin):
    list_display = ("name", "emoji", "trip_count", "is_featured", "thumbnail")
    list_editable = ("is_featured",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "description")
    readonly_fields = ("thumbnail",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(n=Count("packages"))

    @admin.display(description="Trips", ordering="n")
    def trip_count(self, obj):
        return obj.n


@admin.register(Destination)
class DestinationAdmin(ThumbnailMixin, admin.ModelAdmin):
    list_display = (
        "name", "country", "region", "trip_count", "is_featured", "is_active", "thumbnail",
    )
    list_filter = ("is_featured", "is_active", "country")
    list_editable = ("is_featured", "is_active")
    search_fields = ("name", "country", "region", "tagline", "description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [DestinationImageInline, PackageInline]
    readonly_fields = ("thumbnail", "created_at", "updated_at")
    actions = ("feature_destinations", "unfeature_destinations")
    save_on_top = True

    fieldsets = (
        ("The basics", {
            "fields": ("name", "slug", "country", "region", "tagline", "description"),
        }),
        ("Cover photo", {
            "fields": ("thumbnail", "image", "image_url"),
            "description": "Upload a file, or paste a URL if the photo lives elsewhere.",
        }),
        ("Travel details", {"fields": ("best_time_to_visit", "latitude", "longitude")}),
        ("Visibility", {"fields": ("is_featured", "is_active")}),
        ("Search engines (optional)", {
            "classes": ("collapse",),
            "fields": ("meta_title", "meta_description"),
        }),
        ("History", {"classes": ("collapse",), "fields": ("created_at", "updated_at")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(n=Count("packages"))

    @admin.display(description="Trips", ordering="n")
    def trip_count(self, obj):
        return obj.n

    @admin.action(description="Show on the homepage")
    def feature_destinations(self, request, queryset):
        count = queryset.update(is_featured=True)
        self.message_user(request, f"{count} destination(s) now featured.")

    @admin.action(description="Remove from the homepage")
    def unfeature_destinations(self, request, queryset):
        count = queryset.update(is_featured=False)
        self.message_user(request, f"{count} destination(s) unfeatured.")


@admin.register(Package)
class PackageAdmin(ThumbnailMixin, admin.ModelAdmin):
    list_display = (
        "title", "destination", "price_column", "duration_label",
        "rating_column", "is_featured", "is_active", "thumbnail",
    )
    list_filter = ("is_active", "is_featured", "difficulty", "categories", "destination__country")
    list_editable = ("is_featured", "is_active")
    search_fields = ("title", "summary", "description", "destination__name")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("destination",)
    filter_horizontal = ("categories",)
    inlines = [ItineraryDayInline, PackageImageInline]
    readonly_fields = ("thumbnail", "created_at", "updated_at")
    actions = ("activate", "deactivate", "clear_discount")
    save_on_top = True
    list_per_page = 25

    fieldsets = (
        ("The trip", {
            "fields": ("title", "slug", "destination", "categories", "summary", "description"),
        }),
        ("Cover photo", {"fields": ("thumbnail", "image", "image_url")}),
        ("Pricing", {
            "fields": ("price", "discount_price"),
            "description": "Discount price is optional — leave it empty for full price.",
        }),
        ("Length & group size", {
            "fields": (
                ("duration_days", "duration_nights"),
                ("min_guests", "max_guests"),
                "difficulty",
            )
        }),
        ("What's included", {"fields": ("highlights", "inclusions", "exclusions")}),
        ("Availability", {"fields": ("available_from", "available_to")}),
        ("Visibility", {"fields": ("is_featured", "is_active")}),
        ("Search engines (optional)", {
            "classes": ("collapse",), "fields": ("meta_title", "meta_description"),
        }),
        ("History", {"classes": ("collapse",), "fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Price", ordering="price")
    def price_column(self, obj):
        if obj.is_discounted:
            return format_html(
                '<span style="text-decoration:line-through;opacity:.55">{}</span> '
                '<strong style="color:#0a7">{}</strong>',
                f"{obj.price:,.0f}", f"{obj.discount_price:,.0f}",
            )
        return format_html("<strong>{}</strong>", f"{obj.price:,.0f}")

    @admin.display(description="Rating")
    def rating_column(self, obj):
        avg = obj.average_rating
        if not avg:
            return "—"
        return format_html("{} ★ ({})", avg, obj.review_total)

    @admin.action(description="Publish selected trips")
    def activate(self, request, queryset):
        self.message_user(request, f"{queryset.update(is_active=True)} trip(s) published.")

    @admin.action(description="Unpublish selected trips")
    def deactivate(self, request, queryset):
        self.message_user(request, f"{queryset.update(is_active=False)} trip(s) hidden.")

    @admin.action(description="End the sale (clear discount price)")
    def clear_discount(self, request, queryset):
        self.message_user(
            request, f"Sale ended on {queryset.update(discount_price=None)} trip(s)."
        )


@admin.register(ItineraryDay)
class ItineraryDayAdmin(admin.ModelAdmin):
    list_display = ("package", "day_number", "title")
    list_filter = ("package__destination",)
    search_fields = ("title", "description", "package__title")
    autocomplete_fields = ("package",)
