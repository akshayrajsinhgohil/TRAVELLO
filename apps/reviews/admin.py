from django.contrib import admin
from django.utils.html import format_html

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        "title", "stars", "package", "author", "verified", "is_approved", "created_at",
    )
    list_filter = ("is_approved", "rating", "created_at", "package__destination__country")
    list_editable = ("is_approved",)
    search_fields = ("title", "comment", "user__username", "user__email", "package__title")
    autocomplete_fields = ("package", "user")
    readonly_fields = ("created_at", "updated_at", "booking")
    date_hierarchy = "created_at"
    actions = ("approve_reviews", "reject_reviews")
    list_select_related = ("user", "package")
    list_per_page = 30

    fieldsets = (
        ("The review", {"fields": ("package", "user", "rating", "title", "comment")}),
        ("Moderation", {
            "fields": ("is_approved", "staff_note", "booking"),
            "description": "Approve to publish on the trip page.",
        }),
        ("History", {"classes": ("collapse",), "fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Rating", ordering="rating")
    def stars(self, obj):
        return format_html('<span style="color:#e6a700">{}</span>', obj.star_string)

    @admin.display(description="Author", ordering="user__username")
    def author(self, obj):
        return obj.user.get_full_name() or obj.user.username

    @admin.display(description="Verified", boolean=True)
    def verified(self, obj):
        return obj.is_verified

    @admin.action(description="Approve and publish")
    def approve_reviews(self, request, queryset):
        count = queryset.update(is_approved=True)
        self.message_user(request, f"{count} review(s) published.")

    @admin.action(description="Unpublish (hide from the site)")
    def reject_reviews(self, request, queryset):
        count = queryset.update(is_approved=False)
        self.message_user(request, f"{count} review(s) hidden.")
