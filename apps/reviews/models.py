"""Traveller reviews. New reviews are held for moderation before they appear."""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Review(models.Model):
    RATING_CHOICES = [
        (5, "5 — Perfect"),
        (4, "4 — Great"),
        (3, "3 — Fine"),
        (2, "2 — Disappointing"),
        (1, "1 — Avoid"),
    ]

    package = models.ForeignKey(
        "destinations.Package", on_delete=models.CASCADE, related_name="reviews"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews"
    )
    booking = models.ForeignKey(
        "bookings.Booking", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviews",
        help_text="Links the review to a real trip, which marks it as verified.",
    )
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    title = models.CharField(max_length=120)
    comment = models.TextField()
    is_approved = models.BooleanField(
        default=False, help_text="Only approved reviews appear on the site."
    )
    staff_note = models.CharField(
        max_length=200, blank=True, help_text="Internal only — travellers never see this."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        unique_together = ("package", "user")
        indexes = [models.Index(fields=["is_approved", "-created_at"])]

    def __str__(self):
        return f"{self.rating}★ {self.title} — {self.package.title}"

    @property
    def is_verified(self):
        return self.booking_id is not None

    @property
    def star_string(self):
        return "★" * self.rating + "☆" * (5 - self.rating)
