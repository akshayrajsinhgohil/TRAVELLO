from django import forms

from apps.accounts.forms import StyledFormMixin

from .models import ContactMessage, NewsletterSubscriber


class ContactForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ("name", "email", "phone", "topic", "booking_reference", "message")
        widgets = {
            "message": forms.Textarea(
                attrs={"rows": 5, "placeholder": "Tell us what you need."}
            ),
            "booking_reference": forms.TextInput(attrs={"placeholder": "TRV1A2B3C"}),
        }
        labels = {
            "topic": "What's this about?",
            "booking_reference": "Booking reference (if you have one)",
        }


class NewsletterForm(forms.ModelForm):
    class Meta:
        model = NewsletterSubscriber
        fields = ("email",)
        widgets = {
            "email": forms.EmailInput(
                attrs={
                    "placeholder": "you@example.com",
                    "class": (
                        "w-full rounded-full border border-white/12 bg-white/5 px-5 py-3 "
                        "text-sm text-cream placeholder-mist/50 outline-none "
                        "focus:border-mint/60"
                    ),
                }
            )
        }

    def clean_email(self):
        return self.cleaned_data["email"].lower()
