"""Booking tests: price maths, checkout, payment callback and cancellation."""

import json
from datetime import timedelta
from decimal import Decimal

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.core.test_factories import (
    make_booking,
    make_coupon,
    make_package,
    make_user,
)

from .gateways import SandboxGateway, get_gateway
from .models import Booking, Coupon, Payment


@override_settings(TAX_PERCENT=5)
class PricingTests(TestCase):
    """Package.quote() is the single source of truth for money."""

    def setUp(self):
        self.package = make_package(price="10000")

    def test_base_price_times_guests_plus_tax(self):
        quote = self.package.quote(guests=2)

        self.assertEqual(quote["base_amount"], Decimal("20000.00"))
        self.assertEqual(quote["discount_amount"], Decimal("0.00"))
        self.assertEqual(quote["tax_amount"], Decimal("1000.00"))
        self.assertEqual(quote["total_amount"], Decimal("21000.00"))

    def test_discount_price_wins_when_set(self):
        package = make_package(title="On Offer", price="10000", discount_price="8000")

        quote = package.quote(guests=1)

        self.assertEqual(quote["unit_price"], Decimal("8000"))
        self.assertEqual(quote["total_amount"], Decimal("8400.00"))
        self.assertTrue(package.is_discounted)
        self.assertEqual(package.discount_percent, 20)

    def test_percentage_coupon_comes_off_before_tax(self):
        coupon = make_coupon(code="TEN", discount_type="percent", value="10")

        quote = self.package.quote(guests=2, coupon=coupon)

        self.assertEqual(quote["discount_amount"], Decimal("2000.00"))
        # Tax is charged on 18,000 rather than 20,000.
        self.assertEqual(quote["tax_amount"], Decimal("900.00"))
        self.assertEqual(quote["total_amount"], Decimal("18900.00"))

    def test_percentage_coupon_respects_its_cap(self):
        coupon = make_coupon(
            code="BIG", discount_type="percent", value="50", max_discount="3000"
        )

        quote = self.package.quote(guests=2, coupon=coupon)

        self.assertEqual(quote["discount_amount"], Decimal("3000.00"))

    def test_flat_coupon_never_exceeds_the_subtotal(self):
        coupon = make_coupon(code="HUGE", discount_type="flat", value="999999")

        quote = self.package.quote(guests=1, coupon=coupon)

        self.assertEqual(quote["discount_amount"], Decimal("10000.00"))
        self.assertEqual(quote["total_amount"], Decimal("0.00"))

    def test_expired_coupon_is_worth_nothing(self):
        coupon = make_coupon(
            code="OLD",
            value="50",
            valid_from=timezone.localdate() - timedelta(days=40),
            valid_to=timezone.localdate() - timedelta(days=10),
        )

        self.assertFalse(coupon.is_valid)
        self.assertEqual(coupon.discount_for(Decimal("10000")), Decimal("0.00"))

    def test_exhausted_coupon_is_worth_nothing(self):
        coupon = make_coupon(code="GONE", usage_limit=1)
        Coupon.objects.filter(pk=coupon.pk).update(times_used=1)
        coupon.refresh_from_db()

        self.assertFalse(coupon.is_valid)

    def test_guest_count_is_floored_at_one(self):
        self.assertEqual(self.package.quote(guests=0)["guests"], 1)


class BookingModelTests(TestCase):
    def setUp(self):
        self.package = make_package(price="5000", duration_days=4)

    def test_reference_is_generated_and_unique(self):
        first = make_booking(package=self.package)
        second = make_booking(user=make_user("second"), package=self.package)

        self.assertTrue(first.reference.startswith("TRV"))
        self.assertNotEqual(first.reference, second.reference)

    def test_end_date_follows_the_trip_length(self):
        booking = make_booking(package=self.package, start_in_days=10)

        self.assertEqual(booking.end_date, booking.start_date + timedelta(days=3))

    def test_guests_is_adults_plus_children(self):
        booking = make_booking(package=self.package, adults=2, children=3)
        self.assertEqual(booking.guests, 5)

    def test_future_bookings_are_cancellable(self):
        self.assertTrue(make_booking(package=self.package, start_in_days=20).is_cancellable)

    def test_past_bookings_are_not_cancellable(self):
        booking = make_booking(package=self.package)
        Booking.objects.filter(pk=booking.pk).update(
            start_date=timezone.localdate() - timedelta(days=2)
        )
        booking.refresh_from_db()

        self.assertFalse(booking.is_cancellable)

    def test_mark_paid_confirms_and_counts_the_coupon(self):
        coupon = make_coupon(code="USEME")
        booking = make_booking(package=self.package, coupon=coupon)
        booking.coupon = coupon
        booking.save()

        booking.mark_paid()
        booking.refresh_from_db()
        coupon.refresh_from_db()

        self.assertEqual(booking.status, Booking.STATUS_CONFIRMED)
        self.assertEqual(booking.payment_status, Booking.PAYMENT_PAID)
        self.assertEqual(coupon.times_used, 1)


class CheckoutFlowTests(TestCase):
    """The whole path: form → booking → gateway → confirmation."""

    def setUp(self):
        self.user = make_user(username="aanya")
        self.package = make_package(price="10000", max_guests=6)
        self.client.login(username="aanya", password="Tr@vello-2026")
        self.url = reverse("bookings:checkout", kwargs={"slug": self.package.slug})
        self.start = (timezone.localdate() + timedelta(days=30)).isoformat()

    def _payload(self, **overrides):
        payload = {
            "start_date": self.start,
            "adults": 2,
            "children": 0,
            "full_name": "Aanya Kulkarni",
            "email": "aanya@example.com",
            "phone": "+91 9812345678",
            "special_requests": "",
            "coupon_code": "",
        }
        payload.update(overrides)
        return payload

    def test_checkout_requires_a_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_checkout_page_renders_with_a_quote(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "bookings/checkout.html")
        self.assertEqual(response.context["quote"]["guests"], 2)

    @override_settings(TAX_PERCENT=5)
    def test_posting_the_form_creates_a_priced_booking(self):
        response = self.client.post(self.url, self._payload())

        booking = Booking.objects.get()
        self.assertRedirects(
            response,
            reverse("bookings:pay", kwargs={"reference": booking.reference}),
            fetch_redirect_response=False,
        )
        self.assertEqual(booking.user, self.user)
        self.assertEqual(booking.package, self.package)
        self.assertEqual(booking.base_amount, Decimal("20000.00"))
        self.assertEqual(booking.tax_amount, Decimal("1000.00"))
        self.assertEqual(booking.total_amount, Decimal("21000.00"))
        self.assertEqual(booking.status, Booking.STATUS_PENDING)
        self.assertEqual(booking.payment_status, Booking.PAYMENT_UNPAID)

    @override_settings(TAX_PERCENT=5)
    def test_a_valid_coupon_is_applied_and_stored(self):
        make_coupon(code="FIRSTTRIP", discount_type="percent", value="15")

        self.client.post(self.url, self._payload(coupon_code="firsttrip"))

        booking = Booking.objects.get()
        self.assertEqual(booking.coupon.code, "FIRSTTRIP")
        self.assertEqual(booking.discount_amount, Decimal("3000.00"))
        self.assertEqual(booking.total_amount, Decimal("17850.00"))

    def test_an_unknown_coupon_blocks_the_form(self):
        response = self.client.post(self.url, self._payload(coupon_code="NOPE"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Booking.objects.exists())
        self.assertFormError(
            response.context["form"], "coupon_code", "That code isn't valid right now."
        )

    def test_dates_in_the_past_are_refused(self):
        past = (timezone.localdate() - timedelta(days=1)).isoformat()

        response = self.client.post(self.url, self._payload(start_date=past))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Booking.objects.exists())
        self.assertFormError(
            response.context["form"], "start_date", "Pick a date in the future."
        )

    def test_oversized_groups_are_refused(self):
        response = self.client.post(self.url, self._payload(adults=6, children=4))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Booking.objects.exists())
        self.assertIn("adults", response.context["form"].errors)

    def test_inactive_trips_cannot_be_booked(self):
        self.package.is_active = False
        self.package.save()

        self.assertEqual(self.client.get(self.url).status_code, 404)

    @override_settings(TAX_PERCENT=5)
    def test_live_quote_endpoint_returns_the_same_numbers(self):
        make_coupon(code="TEN", value="10")
        url = reverse("bookings:quote", kwargs={"slug": self.package.slug})

        response = self.client.get(url, {"guests": 2, "coupon": "TEN"})

        payload = json.loads(response.content)
        self.assertEqual(payload["total_amount"], "18900.00")
        self.assertTrue(payload["coupon_applied"])

    def test_live_quote_ignores_a_bad_code_rather_than_erroring(self):
        url = reverse("bookings:quote", kwargs={"slug": self.package.slug})

        payload = json.loads(self.client.get(url, {"guests": 1, "coupon": "XX"}).content)

        self.assertFalse(payload["coupon_applied"])


class PaymentTests(TestCase):
    def setUp(self):
        self.user = make_user(username="rohan")
        self.package = make_package(price="12000")
        self.booking = make_booking(user=self.user, package=self.package)
        self.client.login(username="rohan", password="Tr@vello-2026")

    def test_sandbox_is_the_default_gateway(self):
        self.assertIsInstance(get_gateway(), SandboxGateway)

    def test_pay_page_creates_a_payment_record(self):
        response = self.client.get(
            reverse("bookings:pay", kwargs={"reference": self.booking.reference})
        )

        self.assertEqual(response.status_code, 200)
        payment = Payment.objects.get(booking=self.booking)
        self.assertEqual(payment.gateway, "sandbox")
        self.assertEqual(payment.status, Payment.STATUS_CREATED)
        self.assertEqual(payment.amount, self.booking.total_amount)

    def test_successful_callback_confirms_and_emails(self):
        self.client.get(reverse("bookings:pay", kwargs={"reference": self.booking.reference}))
        payment = Payment.objects.get(booking=self.booking)
        mail.outbox.clear()

        response = self.client.post(
            reverse("bookings:callback", kwargs={"reference": self.booking.reference}),
            {"order_id": payment.order_id, "payment_id": "pay_123", "signature": "sig"},
        )

        self.assertRedirects(
            response,
            reverse("bookings:confirmation", kwargs={"reference": self.booking.reference}),
            fetch_redirect_response=False,
        )
        self.booking.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.STATUS_CONFIRMED)
        self.assertEqual(self.booking.payment_status, Booking.PAYMENT_PAID)
        self.assertEqual(payment.status, Payment.STATUS_SUCCESS)
        self.assertEqual(payment.payment_id, "pay_123")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.booking.reference, mail.outbox[0].subject)

    def test_a_callback_with_no_order_id_fails_the_booking(self):
        self.client.get(reverse("bookings:pay", kwargs={"reference": self.booking.reference}))

        self.client.post(
            reverse("bookings:callback", kwargs={"reference": self.booking.reference}),
            {"order_id": "", "payment_id": "", "signature": ""},
        )

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.payment_status, Booking.PAYMENT_FAILED)
        self.assertNotEqual(self.booking.status, Booking.STATUS_CONFIRMED)

    def test_already_paid_bookings_skip_straight_to_confirmation(self):
        self.booking.mark_paid()

        response = self.client.get(
            reverse("bookings:pay", kwargs={"reference": self.booking.reference})
        )

        self.assertRedirects(
            response,
            reverse("bookings:confirmation", kwargs={"reference": self.booking.reference}),
            fetch_redirect_response=False,
        )

    def test_callbacks_must_be_posted(self):
        url = reverse("bookings:callback", kwargs={"reference": self.booking.reference})
        self.assertEqual(self.client.get(url).status_code, 405)


class BookingOwnershipTests(TestCase):
    """One traveller must never see or touch another's booking."""

    def setUp(self):
        self.owner = make_user(username="owner")
        self.stranger = make_user(username="stranger")
        self.booking = make_booking(user=self.owner)

    def test_a_stranger_gets_a_404_not_someone_elses_trip(self):
        self.client.login(username="stranger", password="Tr@vello-2026")

        for name in ("detail", "pay", "confirmation"):
            with self.subTest(view=name):
                response = self.client.get(
                    reverse(f"bookings:{name}", kwargs={"reference": self.booking.reference})
                )
                self.assertEqual(response.status_code, 404)

    def test_a_stranger_cannot_cancel_it(self):
        self.client.login(username="stranger", password="Tr@vello-2026")

        response = self.client.post(
            reverse("bookings:cancel", kwargs={"reference": self.booking.reference})
        )

        self.assertEqual(response.status_code, 404)
        self.booking.refresh_from_db()
        self.assertNotEqual(self.booking.status, Booking.STATUS_CANCELLED)


class CancellationTests(TestCase):
    def setUp(self):
        self.user = make_user(username="meera")
        self.booking = make_booking(user=self.user, start_in_days=45)
        self.client.login(username="meera", password="Tr@vello-2026")
        self.url = reverse(
            "bookings:cancel", kwargs={"reference": self.booking.reference}
        )

    def test_cancelling_an_unpaid_booking(self):
        response = self.client.post(self.url, {"reason": "Changed my mind"})

        self.assertRedirects(response, reverse("bookings:list"))
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.STATUS_CANCELLED)
        self.assertEqual(self.booking.payment_status, Booking.PAYMENT_UNPAID)
        self.assertEqual(self.booking.cancellation_reason, "Changed my mind")

    def test_cancelling_a_paid_booking_marks_a_refund(self):
        self.booking.mark_paid()

        self.client.post(self.url, {"reason": "Visa refused"})

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.STATUS_CANCELLED)
        self.assertEqual(self.booking.payment_status, Booking.PAYMENT_REFUNDED)

    def test_departed_trips_cannot_be_cancelled_online(self):
        Booking.objects.filter(pk=self.booking.pk).update(
            start_date=timezone.localdate() - timedelta(days=1)
        )

        self.client.post(self.url, {"reason": "Too late"})

        self.booking.refresh_from_db()
        self.assertNotEqual(self.booking.status, Booking.STATUS_CANCELLED)


class BookingListTests(TestCase):
    def setUp(self):
        self.user = make_user(username="dev")
        self.package = make_package()
        self.upcoming = make_booking(
            user=self.user, package=self.package, start_in_days=30
        )
        self.past = make_booking(user=self.user, package=self.package, start_in_days=10)
        Booking.objects.filter(pk=self.past.pk).update(
            start_date=timezone.localdate() - timedelta(days=30)
        )
        self.client.login(username="dev", password="Tr@vello-2026")

    def test_all_tab_shows_everything(self):
        response = self.client.get(reverse("bookings:list"))
        self.assertEqual(len(response.context["bookings"]), 2)

    def test_upcoming_tab_filters_correctly(self):
        response = self.client.get(reverse("bookings:list"), {"show": "upcoming"})

        references = [b.reference for b in response.context["bookings"]]
        self.assertEqual(references, [self.upcoming.reference])

    def test_past_tab_filters_correctly(self):
        response = self.client.get(reverse("bookings:list"), {"show": "past"})

        references = [b.reference for b in response.context["bookings"]]
        self.assertEqual(references, [self.past.reference])

    def test_you_only_ever_see_your_own(self):
        make_booking(user=make_user("someone-else"), package=self.package)

        response = self.client.get(reverse("bookings:list"))

        self.assertEqual(len(response.context["bookings"]), 2)
