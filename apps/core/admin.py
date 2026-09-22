from django.contrib import admin
from django.utils.html import format_html

from .models import ContactMessage, NewsletterSubscriber, Testimonial


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("name", "trip_taken", "rating", "is_active", "order")
    list_editable = ("is_active", "order")
    list_filter = ("is_active", "rating")
    search_fields = ("name", "quote", "trip_taken")


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "source", "is_active", "created_at")
    list_filter = ("is_active", "source", "created_at")
    search_fields = ("email",)
    actions = ("export_emails",)

    @admin.action(description="Show selected emails as a copy-paste list")
    def export_emails(self, request, queryset):
        emails = ", ".join(queryset.values_list("email", flat=True))
        self.message_user(request, emails or "No subscribers selected.")


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "topic", "email", "reference_column", "is_resolved", "created_at")
    list_filter = ("is_resolved", "topic", "created_at")
    list_editable = ("is_resolved",)
    search_fields = ("name", "email", "message", "booking_reference")
    readonly_fields = ("name", "email", "phone", "topic", "booking_reference",
                       "message", "created_at")
    actions = ("mark_resolved",)
    date_hierarchy = "created_at"

    fieldsets = (
        ("Message", {"fields": ("name", "email", "phone", "topic",
                                "booking_reference", "message", "created_at")}),
        ("Handling", {"fields": ("is_resolved", "staff_note")}),
    )

    @admin.display(description="Booking")
    def reference_column(self, obj):
        return format_html("<code>{}</code>", obj.booking_reference or "—")

    @admin.action(description="Mark as resolved")
    def mark_resolved(self, request, queryset):
        count = queryset.update(is_resolved=True)
        self.message_user(request, f"{count} message(s) resolved.")

    def has_add_permission(self, request):
        return False
