"""Booking, coupon and payment records."""

import secrets
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Coupon(models.Model):
    """A discount code staff can hand out."""

    DISCOUNT_TYPES = [("percent", "Percentage off"), ("flat", "Flat amount off")]

    code = models.CharField(max_length=24, unique=True)
    description = models.CharField(max_length=140, blank=True)
    discount_type = models.CharField(
        max_length=10, choices=DISCOUNT_TYPES, default="percent"
    )
    value = models.DecimalField(
        max_digits=8, decimal_places=2,
        help_text="15 means 15% off, or a flat 15 depending on the type above.",
    )
    max_discount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Optional cap for percentage discounts.",
    )
    valid_from = models.DateField(default=timezone.now)
    valid_to = models.DateField()
    usage_limit = models.PositiveIntegerField(default=100)
    times_used = models.PositiveIntegerField(default=0, editable=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("-valid_to",)

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        self.code = self.code.upper().strip()
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        today = timezone.localdate()
        return (
            self.is_active
            and self.valid_from <= today <= self.valid_to
            and self.times_used < self.usage_limit
        )

    def discount_for(self, amount: Decimal) -> Decimal:
        """How much comes off a given subtotal."""
        if not self.is_valid:
            return Decimal("0.00")
        amount = Decimal(str(amount))
        value = Decimal(str(self.value))
        if self.discount_type == "flat":
            discount = min(value, amount)
        else:
            discount = amount * value / Decimal(100)
            if self.max_discount:
                discount = min(discount, Decimal(str(self.max_discount)))
        return discount.quantize(Decimal("0.01"))


class BookingQuerySet(models.QuerySet):
    def paid(self):
        return self.filter(payment_status=Booking.PAYMENT_PAID)

    def active(self):
        return self.exclude(status__in=[Booking.STATUS_CANCELLED, Booking.STATUS_REFUNDED])

    def upcoming(self):
        return self.active().filter(start_date__gte=timezone.localdate()).order_by("start_date")

    def past(self):
        return self.filter(start_date__lt=timezone.localdate())


class Booking(models.Model):
    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_CANCELLED = "cancelled"
    STATUS_COMPLETED = "completed"
    STATUS_REFUNDED = "refunded"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Awaiting payment"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_REFUNDED, "Refunded"),
    ]

    PAYMENT_UNPAID = "unpaid"
    PAYMENT_PAID = "paid"
    PAYMENT_FAILED = "failed"
    PAYMENT_REFUNDED = "refunded"
    PAYMENT_CHOICES = [
        (PAYMENT_UNPAID, "Not paid"),
        (PAYMENT_PAID, "Paid"),
        (PAYMENT_FAILED, "Failed"),
        (PAYMENT_REFUNDED, "Refunded"),
    ]

    reference = models.CharField(max_length=12, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bookings"
    )
    package = models.ForeignKey(
        "destinations.Package", on_delete=models.PROTECT, related_name="bookings"
    )

    start_date = models.DateField()
    end_date = models.DateField(editable=False)
    adults = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1)])
    children = models.PositiveSmallIntegerField(default=0)

    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    special_requests = models.TextField(blank=True)

    coupon = models.ForeignKey(
        Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name="bookings"
    )
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    base_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_PENDING)
    payment_status = models.CharField(
        max_length=12, choices=PAYMENT_CHOICES, default=PAYMENT_UNPAID
    )
    cancellation_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = BookingQuerySet.as_manager()

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["reference"]),
            models.Index(fields=["status", "payment_status"]),
        ]

    def __str__(self):
        return f"{self.reference} — {self.package.title}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self._new_reference()
        # The trip length defines the end date, so it is never entered by hand.
        self.end_date = self.start_date + timedelta(days=max(self.package.duration_days - 1, 0))
        super().save(*args, **kwargs)

    @staticmethod
    def _new_reference():
        while True:
            ref = "TRV" + secrets.token_hex(3).upper()[:6]
            if not Booking.objects.filter(reference=ref).exists():
                return ref

    def clean(self):
        if self.start_date and self.start_date < timezone.localdate():
            raise ValidationError({"start_date": "Pick a date in the future."})
        if self.package_id and self.guests > self.package.max_guests:
            raise ValidationError(
                {"adults": f"This trip takes up to {self.package.max_guests} guests."}
            )

    def get_absolute_url(self):
        return reverse("bookings:detail", kwargs={"reference": self.reference})

    @property
    def guests(self):
        return self.adults + self.children

    @property
    def is_cancellable(self):
        return (
            self.status in (self.STATUS_PENDING, self.STATUS_CONFIRMED)
            and self.start_date > timezone.localdate()
        )

    @property
    def days_until(self):
        return (self.start_date - timezone.localdate()).days

    @property
    def status_tone(self):
        """Maps status to a palette token so templates stay free of logic."""
        return {
            self.STATUS_CONFIRMED: "mint",
            self.STATUS_COMPLETED: "violet",
            self.STATUS_PENDING: "amber",
            self.STATUS_CANCELLED: "magenta",
            self.STATUS_REFUNDED: "magenta",
        }.get(self.status, "mist")

    def mark_paid(self):
        self.payment_status = self.PAYMENT_PAID
        self.status = self.STATUS_CONFIRMED
        self.save(update_fields=["payment_status", "status", "updated_at"])
        if self.coupon:
            Coupon.objects.filter(pk=self.coupon_id).update(
                times_used=models.F("times_used") + 1
            )


class Payment(models.Model):
    """One payment attempt against a booking."""

    STATUS_CREATED = "created"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_REFUNDED = "refunded"
    STATUS_CHOICES = [
        (STATUS_CREATED, "Started"),
        (STATUS_SUCCESS, "Successful"),
        (STATUS_FAILED, "Failed"),
        (STATUS_REFUNDED, "Refunded"),
    ]

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="payments")
    gateway = models.CharField(max_length=20, default="sandbox")
    order_id = models.CharField(max_length=120, blank=True)
    payment_id = models.CharField(max_length=120, blank=True)
    signature = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=8, default="INR")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_CREATED)
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.gateway}:{self.order_id or self.pk} ({self.status})"
