"""Catalogue models: categories, destinations, trip packages and itineraries.

Image fields accept either an upload or a remote URL. That keeps the seed
fixtures light (no binaries in the repo) while letting staff drag-and-drop
real photos in the admin later.
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg, Count
from django.urls import reverse
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ImageFallbackMixin(models.Model):
    """Gives a model an uploaded image with a remote-URL fallback."""

    image = models.ImageField(upload_to="catalogue/", blank=True, null=True)
    image_url = models.URLField(
        blank=True,
        help_text="Optional. Used when no file is uploaded — handy for seed data.",
    )

    class Meta:
        abstract = True

    @property
    def display_image(self):
        if self.image:
            return self.image.url
        return self.image_url or ""


class Category(ImageFallbackMixin, TimeStampedModel):
    """A way to travel: beaches, treks, road trips, heritage..."""

    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True, blank=True)
    emoji = models.CharField(
        max_length=8, blank=True, help_text="Shown on category chips, e.g. 🏔️"
    )
    description = models.CharField(max_length=200, blank=True)
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return f"{reverse('destinations:package_list')}?category={self.slug}"


class DestinationQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_active=True)

    def featured(self):
        return self.published().filter(is_featured=True)

    def with_trip_stats(self):
        return self.annotate(
            trip_count=Count("packages", filter=models.Q(packages__is_active=True)),
            avg_rating=Avg("packages__reviews__rating",
                           filter=models.Q(packages__reviews__is_approved=True)),
        )


class Destination(ImageFallbackMixin, TimeStampedModel):
    """A place travellers search for — a city, island or region."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    country = models.CharField(max_length=80)
    region = models.CharField(max_length=80, blank=True, help_text="State or province")
    tagline = models.CharField(
        max_length=140, blank=True, help_text="One line shown on cards and the hero."
    )
    description = models.TextField()
    best_time_to_visit = models.CharField(max_length=120, blank=True)
    latitude = models.FloatField(
        null=True, blank=True, help_text="Used to place the pin on the 3D globe."
    )
    longitude = models.FloatField(null=True, blank=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # SEO
    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)

    objects = DestinationQuerySet.as_manager()

    class Meta:
        ordering = ("name",)
        indexes = [models.Index(fields=["slug"]), models.Index(fields=["country"])]

    def __str__(self):
        return f"{self.name}, {self.country}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.name}-{self.country}")[:120]
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("destinations:destination_detail", kwargs={"slug": self.slug})

    @property
    def seo_title(self):
        return self.meta_title or f"{self.name} trips & packages | Travello"

    @property
    def seo_description(self):
        return self.meta_description or self.tagline or self.description[:155]

    @property
    def starting_price(self):
        cheapest = self.packages.filter(is_active=True).order_by("price").first()
        return cheapest.current_price if cheapest else None


class DestinationImage(models.Model):
    destination = models.ForeignKey(
        Destination, on_delete=models.CASCADE, related_name="gallery"
    )
    image = models.ImageField(upload_to="destinations/", blank=True, null=True)
    image_url = models.URLField(blank=True)
    caption = models.CharField(max_length=140, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("order", "id")

    def __str__(self):
        return self.caption or f"Photo of {self.destination.name}"

    @property
    def display_image(self):
        return self.image.url if self.image else self.image_url


class PackageQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_active=True)

    def featured(self):
        return self.published().filter(is_featured=True)

    def with_ratings(self):
        return self.annotate(
            rating_avg=Avg("reviews__rating", filter=models.Q(reviews__is_approved=True)),
            rating_count=Count("reviews", filter=models.Q(reviews__is_approved=True)),
        )


class Package(ImageFallbackMixin, TimeStampedModel):
    """A bookable trip attached to a destination."""

    DIFFICULTY_CHOICES = [
        ("easy", "Easy — anyone can do this"),
        ("moderate", "Moderate — some walking and early starts"),
        ("challenging", "Challenging — good fitness needed"),
    ]

    destination = models.ForeignKey(
        Destination, on_delete=models.CASCADE, related_name="packages"
    )
    categories = models.ManyToManyField(Category, related_name="packages", blank=True)
    title = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    summary = models.CharField(max_length=200, help_text="One line shown on trip cards.")
    description = models.TextField()

    price = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Full price per person."
    )
    discount_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Leave empty if the trip is not on offer.",
    )

    duration_days = models.PositiveSmallIntegerField(default=3)
    duration_nights = models.PositiveSmallIntegerField(default=2)
    max_guests = models.PositiveSmallIntegerField(default=12)
    min_guests = models.PositiveSmallIntegerField(default=1)
    difficulty = models.CharField(
        max_length=20, choices=DIFFICULTY_CHOICES, default="easy"
    )

    inclusions = models.TextField(
        blank=True, help_text="One item per line — shown as a checklist."
    )
    exclusions = models.TextField(blank=True, help_text="One item per line.")
    highlights = models.TextField(blank=True, help_text="One highlight per line.")

    available_from = models.DateField(null=True, blank=True)
    available_to = models.DateField(null=True, blank=True)

    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(
        default=True, help_text="Untick to hide this trip from the site."
    )

    meta_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)

    objects = PackageQuerySet.as_manager()

    class Meta:
        ordering = ("-is_featured", "-created_at")
        indexes = [models.Index(fields=["slug"]), models.Index(fields=["price"])]
        verbose_name = "trip package"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:150]
            slug, counter = base, 2
            while Package.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("destinations:package_detail", kwargs={"slug": self.slug})

    # -- pricing -----------------------------------------------------------
    @property
    def current_price(self) -> Decimal:
        # Coerced explicitly: a DecimalField set from a form or API call holds
        # whatever was assigned until the row is re-fetched, and every caller
        # here goes on to do arithmetic with it.
        price = self.discount_price if self.discount_price else self.price
        return Decimal(str(price))

    @property
    def is_discounted(self) -> bool:
        if not self.discount_price:
            return False
        return Decimal(str(self.discount_price)) < Decimal(str(self.price))

    @property
    def discount_percent(self) -> int:
        if not self.is_discounted:
            return 0
        full = Decimal(str(self.price))
        cut = Decimal(str(self.discount_price))
        return int(round((full - cut) / full * 100))

    # -- display helpers ---------------------------------------------------
    @property
    def duration_label(self) -> str:
        return f"{self.duration_days}D / {self.duration_nights}N"

    def _as_list(self, value):
        return [line.strip() for line in (value or "").splitlines() if line.strip()]

    @property
    def inclusion_list(self):
        return self._as_list(self.inclusions)

    @property
    def exclusion_list(self):
        return self._as_list(self.exclusions)

    @property
    def highlight_list(self):
        return self._as_list(self.highlights)

    @property
    def seo_title(self):
        return self.meta_title or f"{self.title} | {self.destination.name} | Travello"

    @property
    def seo_description(self):
        return self.meta_description or self.summary

    # -- ratings -----------------------------------------------------------
    @property
    def average_rating(self):
        result = self.reviews.filter(is_approved=True).aggregate(a=Avg("rating"))["a"]
        return round(result, 1) if result else None

    @property
    def review_total(self):
        return self.reviews.filter(is_approved=True).count()

    def quote(self, guests: int = 1, coupon=None) -> dict:
        """Price a booking. Returns every line the checkout page shows."""
        guests = max(int(guests or 1), 1)
        base = self.current_price * guests
        discount = Decimal("0.00")
        if coupon is not None:
            discount = coupon.discount_for(base)
        taxable = base - discount
        tax = (taxable * Decimal(settings.TAX_PERCENT) / Decimal(100)).quantize(
            Decimal("0.01")
        )
        return {
            "guests": guests,
            "unit_price": self.current_price,
            "base_amount": base.quantize(Decimal("0.01")),
            "discount_amount": discount.quantize(Decimal("0.01")),
            "tax_amount": tax,
            "total_amount": (taxable + tax).quantize(Decimal("0.01")),
        }


class PackageImage(models.Model):
    package = models.ForeignKey(
        Package, on_delete=models.CASCADE, related_name="gallery"
    )
    image = models.ImageField(upload_to="packages/", blank=True, null=True)
    image_url = models.URLField(blank=True)
    caption = models.CharField(max_length=140, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("order", "id")

    def __str__(self):
        return self.caption or f"Photo {self.order} — {self.package.title}"

    @property
    def display_image(self):
        return self.image.url if self.image else self.image_url


class ItineraryDay(models.Model):
    """One day of a trip, shown as a vertical timeline on the trip page."""

    package = models.ForeignKey(
        Package, on_delete=models.CASCADE, related_name="itinerary"
    )
    day_number = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(60)]
    )
    title = models.CharField(max_length=140)
    description = models.TextField()
    meals = models.CharField(
        max_length=120, blank=True, help_text="e.g. Breakfast, dinner"
    )
    stay = models.CharField(max_length=140, blank=True, help_text="Where guests sleep")

    class Meta:
        ordering = ("day_number",)
        unique_together = ("package", "day_number")
        verbose_name = "itinerary day"
        verbose_name_plural = "itinerary days"

    def __str__(self):
        return f"Day {self.day_number}: {self.title}"
