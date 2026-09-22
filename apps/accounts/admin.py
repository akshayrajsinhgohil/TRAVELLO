from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from .models import User, Wishlist


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username", "email", "first_name", "verified_badge",
        "is_active", "is_staff", "created_at",
    )
    list_filter = ("is_email_verified", "is_active", "is_staff", "newsletter_opt_in")
    search_fields = ("username", "email", "first_name", "last_name", "phone")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "last_login", "date_joined")
    actions = ("mark_email_verified", "deactivate_accounts")

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Traveller profile",
            {
                "fields": (
                    "phone", "avatar", "bio", "date_of_birth",
                    "city", "country", "is_email_verified", "newsletter_opt_in",
                )
            },
        ),
    )

    @admin.display(description="Email", ordering="is_email_verified")
    def verified_badge(self, obj):
        colour = "#35E0C2" if obj.is_email_verified else "#FFB020"
        label = "Confirmed" if obj.is_email_verified else "Unconfirmed"
        return format_html(
            '<span style="color:{};font-weight:600">{}</span>', colour, label
        )

    @admin.action(description="Mark selected emails as confirmed")
    def mark_email_verified(self, request, queryset):
        updated = queryset.update(is_email_verified=True)
        self.message_user(request, f"{updated} account(s) confirmed.")

    @admin.action(description="Deactivate selected accounts")
    def deactivate_accounts(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} account(s) deactivated.")


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("user", "package", "created_at")
    search_fields = ("user__username", "user__email", "package__title")
    autocomplete_fields = ("user", "package")
    list_select_related = ("user", "package")
