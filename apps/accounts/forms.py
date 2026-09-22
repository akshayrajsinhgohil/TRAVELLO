"""Forms for registration, login and profile management."""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

User = get_user_model()

BASE_INPUT = (
    "w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-cream "
    "placeholder-mist/60 outline-none transition focus:border-magenta/60 "
    "focus:ring-2 focus:ring-magenta/25"
)


class StyledFormMixin:
    """Applies the Travello input styling to every widget on the form."""

    default_classes = BASE_INPUT

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
                widget.attrs.setdefault("class", "accent-magenta h-4 w-4 rounded")
                continue
            existing = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{existing} {self.default_classes}".strip()
            if isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("rows", 4)


class RegistrationForm(StyledFormMixin, UserCreationForm):
    first_name = forms.CharField(
        max_length=60, widget=forms.TextInput(attrs={"placeholder": "Aanya"})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"placeholder": "you@example.com"})
    )
    newsletter_opt_in = forms.BooleanField(
        required=False,
        initial=True,
        label="Send me new trips and price drops",
    )

    class Meta:
        model = User
        fields = ("first_name", "username", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account already uses this email. Try signing in instead."
            )
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.newsletter_opt_in = self.cleaned_data.get("newsletter_opt_in", False)
        if commit:
            user.save()
        return user


class LoginForm(StyledFormMixin, AuthenticationForm):
    username = forms.CharField(
        label="Email or username",
        widget=forms.TextInput(attrs={"placeholder": "you@example.com"}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Your password"})
    )


class ProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = (
            "first_name", "last_name", "email", "phone", "avatar",
            "bio", "date_of_birth", "city", "country", "newsletter_opt_in",
        )
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "bio": forms.Textarea(attrs={"placeholder": "Beaches, street food, no 6am alarms."}),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Another account already uses this email.")
        return email
