"""Checkout form."""

from django import forms
from django.utils import timezone

from apps.accounts.forms import StyledFormMixin

from .models import Booking, Coupon


class BookingForm(StyledFormMixin, forms.ModelForm):
    coupon_code = forms.CharField(
        required=False,
        label="Discount code",
        widget=forms.TextInput(attrs={"placeholder": "FIRSTTRIP"}),
    )

    class Meta:
        model = Booking
        fields = (
            "start_date", "adults", "children",
            "full_name", "email", "phone", "special_requests",
        )
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "special_requests": forms.Textarea(
                attrs={"placeholder": "Window seat, vegetarian meals, late check-in…"}
            ),
        }
        labels = {
            "start_date": "Leaving on",
            "adults": "Adults",
            "children": "Children",
            "full_name": "Lead traveller",
            "special_requests": "Anything we should know?",
        }

    def __init__(self, *args, package=None, user=None, **kwargs):
        self.package = package
        self.user = user
        super().__init__(*args, **kwargs)
        today = timezone.localdate().isoformat()
        self.fields["start_date"].widget.attrs["min"] = today
        if package:
            self.fields["adults"].widget.attrs["max"] = package.max_guests
            self.fields["children"].widget.attrs["max"] = package.max_guests
            if package.available_from:
                self.fields["start_date"].widget.attrs["min"] = max(
                    today, package.available_from.isoformat()
                )
            if package.available_to:
                self.fields["start_date"].widget.attrs["max"] = package.available_to.isoformat()
        if user and user.is_authenticated:
            self.fields["full_name"].initial = user.get_full_name() or user.username
            self.fields["email"].initial = user.email
            self.fields["phone"].initial = user.phone

    def clean_start_date(self):
        start = self.cleaned_data["start_date"]
        if start < timezone.localdate():
            raise forms.ValidationError("Pick a date in the future.")
        if self.package and self.package.available_to and start > self.package.available_to:
            raise forms.ValidationError(
                f"This trip runs until {self.package.available_to:%d %b %Y}."
            )
        return start

    def clean_coupon_code(self):
        code = (self.cleaned_data.get("coupon_code") or "").strip().upper()
        if not code:
            return ""
        coupon = Coupon.objects.filter(code=code).first()
        if not coupon or not coupon.is_valid:
            raise forms.ValidationError("That code isn't valid right now.")
        self.coupon = coupon
        return code

    def clean(self):
        cleaned = super().clean()
        adults = cleaned.get("adults") or 0
        children = cleaned.get("children") or 0
        total = adults + children
        if self.package:
            if total > self.package.max_guests:
                self.add_error(
                    "adults",
                    f"This trip takes up to {self.package.max_guests} guests. "
                    f"Email us for larger groups.",
                )
            if total < self.package.min_guests:
                self.add_error(
                    "adults", f"This trip needs at least {self.package.min_guests} guest(s)."
                )
        return cleaned

    def get_coupon(self):
        return getattr(self, "coupon", None)
