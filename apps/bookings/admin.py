"""Booking admin — built around the questions staff actually ask."""

from django.contrib import admin
from django.utils.html import format_html

from .models import Booking, Coupon, Payment


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    can_delete = False
    readonly_fields = ("gateway", "order_id", "payment_id", "amount", "status", "created_at")
    fields = readonly_fields


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "reference", "traveller", "trip", "start_date", "guests",
        "total_column", "status_badge", "payment_badge", "created_at",
    )
    list_filter = (
        "status", "payment_status", "start_date",
        "package__destination__country", "created_at",
    )
    search_fields = (
        "reference", "full_name", "email", "phone",
        "user__username", "user__email", "package__title",
    )
    date_hierarchy = "start_date"
    autocomplete_fields = ("user", "package")
    readonly_fields = (
        "reference", "end_date", "unit_price", "base_amount", "discount_amount",
        "tax_amount", "total_amount", "created_at", "updated_at",
    )
    inlines = [PaymentInline]
    list_select_related = ("user", "package", "package__destination")
    list_per_page = 30
    actions = ("confirm_bookings", "cancel_bookings", "mark_refunded", "mark_completed")
    save_on_top = True

    fieldsets = (
        ("Booking", {"fields": ("reference", "user", "package", "status", "payment_status")}),
        ("Travel dates", {"fields": ("start_date", "end_date", "adults", "children")}),
        ("Who's travelling", {"fields": ("full_name", "email", "phone", "special_requests")}),
        ("Money", {
            "fields": (
                "coupon", "unit_price", "base_amount",
                "discount_amount", "tax_amount", "total_amount",
            ),
            "description": "Totals are calculated at checkout and kept for the record.",
        }),
        ("If cancelled", {"classes": ("collapse",), "fields": ("cancellation_reason",)}),
        ("History", {"classes": ("collapse",), "fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Traveller", ordering="full_name")
    def traveller(self, obj):
        return format_html("{}<br><small>{}</small>", obj.full_name, obj.email)

    @admin.display(description="Trip", ordering="package__title")
    def trip(self, obj):
        return format_html(
            "{}<br><small>{}</small>", obj.package.title, obj.package.destination.name
        )

    @admin.display(description="Total", ordering="total_amount")
    def total_column(self, obj):
        return format_html("<strong>{}</strong>", f"{obj.total_amount:,.0f}")

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        colours = {
            "confirmed": "#0a7", "pending": "#b8860b", "cancelled": "#c23",
            "completed": "#5b3ef0", "refunded": "#c23",
        }
        return format_html(
            '<span style="background:{}22;color:{};padding:3px 10px;'
            'border-radius:99px;font-weight:600;font-size:11px">{}</span>',
            colours.get(obj.status, "#666"), colours.get(obj.status, "#666"),
            obj.get_status_display(),
        )

    @admin.display(description="Payment", ordering="payment_status")
    def payment_badge(self, obj):
        return obj.get_payment_status_display()

    @admin.action(description="Confirm selected bookings")
    def confirm_bookings(self, request, queryset):
        count = queryset.update(status=Booking.STATUS_CONFIRMED)
        self.message_user(request, f"{count} booking(s) confirmed.")

    @admin.action(description="Cancel selected bookings")
    def cancel_bookings(self, request, queryset):
        count = queryset.update(status=Booking.STATUS_CANCELLED)
        self.message_user(request, f"{count} booking(s) cancelled.")

    @admin.action(description="Mark refund as paid out")
    def mark_refunded(self, request, queryset):
        count = queryset.update(
            status=Booking.STATUS_REFUNDED, payment_status=Booking.PAYMENT_REFUNDED
        )
        self.message_user(request, f"{count} booking(s) marked refunded.")

    @admin.action(description="Mark trip as completed")
    def mark_completed(self, request, queryset):
        count = queryset.update(status=Booking.STATUS_COMPLETED)
        self.message_user(request, f"{count} booking(s) completed.")


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        "code", "discount_type", "value", "valid_from", "valid_to",
        "times_used", "usage_limit", "is_active",
    )
    list_filter = ("discount_type", "is_active")
    list_editable = ("is_active",)
    search_fields = ("code", "description")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order_id", "booking", "gateway", "amount", "status", "created_at")
    list_filter = ("gateway", "status", "created_at")
    search_fields = ("order_id", "payment_id", "booking__reference")
    readonly_fields = [f.name for f in Payment._meta.fields]

    def has_add_permission(self, request):
        return False
