"""Search and filter form for the trip listing page."""

from django import forms

from .models import Category, Destination

SELECT = (
    "w-full rounded-xl border border-white/10 bg-ink/60 px-3 py-2.5 text-sm "
    "text-cream outline-none transition focus:border-violet/60"
)


class TripFilterForm(forms.Form):
    SORT_CHOICES = [
        ("popular", "Most booked"),
        ("price_low", "Price: low to high"),
        ("price_high", "Price: high to low"),
        ("rating", "Best rated"),
        ("duration", "Shortest trip"),
    ]

    q = forms.CharField(
        required=False,
        label="Search",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Try “Goa”, “trek”, “houseboat”",
                "class": (
                    "w-full rounded-xl border border-white/10 bg-ink/60 px-4 py-2.5 "
                    "text-sm text-cream placeholder-mist/50 outline-none "
                    "focus:border-magenta/60"
                ),
            }
        ),
    )
    destination = forms.ModelChoiceField(
        queryset=Destination.objects.published(),
        required=False,
        empty_label="Anywhere",
        widget=forms.Select(attrs={"class": SELECT}),
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="Any style",
        to_field_name="slug",
        widget=forms.Select(attrs={"class": SELECT}),
    )
    min_price = forms.DecimalField(
        required=False, min_value=0,
        widget=forms.NumberInput(attrs={"class": SELECT, "placeholder": "Min"}),
    )
    max_price = forms.DecimalField(
        required=False, min_value=0,
        widget=forms.NumberInput(attrs={"class": SELECT, "placeholder": "Max"}),
    )
    start_date = forms.DateField(
        required=False,
        label="Leaving after",
        widget=forms.DateInput(attrs={"type": "date", "class": SELECT}),
    )
    guests = forms.IntegerField(
        required=False, min_value=1, max_value=30,
        widget=forms.NumberInput(attrs={"class": SELECT, "placeholder": "2"}),
    )
    sort = forms.ChoiceField(
        required=False, choices=SORT_CHOICES,
        widget=forms.Select(attrs={"class": SELECT}),
    )

    def clean(self):
        cleaned = super().clean()
        low, high = cleaned.get("min_price"), cleaned.get("max_price")
        if low and high and low > high:
            self.add_error("max_price", "Highest price must be above the lowest.")
        return cleaned
