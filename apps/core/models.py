"""Marketing-side content: testimonials, newsletter list, contact messages."""

from django.db import models
from django.utils import timezone


class Testimonial(models.Model):
    name = models.CharField(max_length=80)
    handle = models.CharField(
        max_length=60, blank=True, help_text="Social handle shown under the name."
    )
    trip_taken = models.CharField(max_length=120, blank=True)
    quote = models.TextField(max_length=400)
    rating = models.PositiveSmallIntegerField(default=5)
    avatar = models.ImageField(upload_to="testimonials/", blank=True, null=True)
    avatar_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("order", "-created_at")

    def __str__(self):
        return f"{self.name} — {self.trip_taken or 'Travello'}"

    @property
    def display_avatar(self):
        return self.avatar.url if self.avatar else self.avatar_url

    @property
    def initials(self):
        return "".join(part[0] for part in self.name.split()[:2]).upper()


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    source = models.CharField(max_length=40, default="footer")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "newsletter subscriber"

    def __str__(self):
        return self.email


class ContactMessage(models.Model):
    TOPIC_CHOICES = [
        ("booking", "A booking I've made"),
        ("trip", "A question about a trip"),
        ("group", "Group or corporate travel"),
        ("partner", "Partnerships"),
        ("other", "Something else"),
    ]

    name = models.CharField(max_length=80)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    topic = models.CharField(max_length=20, choices=TOPIC_CHOICES, default="other")
    booking_reference = models.CharField(max_length=12, blank=True)
    message = models.TextField()
    is_resolved = models.BooleanField(default=False)
    staff_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("is_resolved", "-created_at")
        verbose_name = "support message"

    def __str__(self):
        return f"{self.name} — {self.get_topic_display()}"
