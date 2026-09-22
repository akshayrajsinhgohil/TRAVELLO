from django import forms

from apps.accounts.forms import StyledFormMixin

from .models import Review


class ReviewForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Review
        fields = ("rating", "title", "comment")
        widgets = {
            "rating": forms.RadioSelect(),
            "title": forms.TextInput(
                attrs={"placeholder": "Sum it up in a few words"}
            ),
            "comment": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "What was the trip actually like? What surprised you?",
                }
            ),
        }
        labels = {"rating": "Your rating", "title": "Headline", "comment": "Your review"}

    def clean_comment(self):
        comment = self.cleaned_data["comment"].strip()
        if len(comment) < 30:
            raise forms.ValidationError(
                "Add a bit more detail — at least 30 characters helps other travellers."
            )
        return comment
