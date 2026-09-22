"""User account models.

Travello uses a custom user model from day one so that email can be the
primary login identifier and profile data lives in one place.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils import timezone


class User(AbstractUser):
    """Traveller account. Email is unique and used to sign in."""

    email = models.EmailField("email address", unique=True)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    bio = models.TextField(
        blank=True,
        help_text="A short line about the kind of travel you like.",
    )
    date_of_birth = models.DateField(blank=True, null=True)
    city = models.CharField(max_length=80, blank=True)
    country = models.CharField(max_length=80, blank=True)
    is_email_verified = models.BooleanField(default=False)
    newsletter_opt_in = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    # Email is the login field; username stays for admin compatibility.
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def display_name(self):
        return self.first_name or self.username

    @property
    def initials(self):
        parts = [p for p in (self.first_name, self.last_name) if p]
        if parts:
            return "".join(p[0] for p in parts).upper()
        return self.username[:2].upper()

    @property
    def avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return ""

    def get_absolute_url(self):
        return reverse("accounts:profile")


class Wishlist(models.Model):
    """A trip a traveller saved for later."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wishlist")
    package = models.ForeignKey(
        "destinations.Package", on_delete=models.CASCADE, related_name="wishlisted_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "package")
        ordering = ("-created_at",)
        verbose_name = "saved trip"
        verbose_name_plural = "saved trips"

    def __str__(self):
        return f"{self.user} saved {self.package}"
