"""Marketing pages, newsletter, contact form and the staff analytics dashboard."""

import json

from django.test import TestCase
from django.urls import reverse

from apps.bookings.models import Booking
from apps.core.test_factories import make_booking, make_destination, make_package, make_user

from .models import ContactMessage, NewsletterSubscriber, Testimonial


class HomePageTests(TestCase):
    def setUp(self):
        self.destination = make_destination("Bali", "Indonesia", is_featured=True)
        self.package = make_package(
            destination=self.destination, title="Bali Unfiltered", is_featured=True
        )
        Testimonial.objects.create(
            name="Aanya K", quote="The pacing was perfect.", rating=5
        )

    def test_home_renders_with_featured_content(self):
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/home.html")
        self.assertContains(response, "Bali Unfiltered")
        self.assertContains(response, "The pacing was perfect.")

    def test_hidden_trips_stay_off_the_home_page(self):
        self.package.is_active = False
        self.package.save()

        response = self.client.get(reverse("core:home"))

        self.assertNotContains(response, "Bali Unfiltered")

    def test_about_page_renders(self):
        self.assertEqual(self.client.get(reverse("core:about")).status_code, 200)

    def test_missing_pages_use_the_custom_404(self):
        response = self.client.get("/this-does-not-exist/")
        self.assertEqual(response.status_code, 404)


class NewsletterTests(TestCase):
    url = reverse("core:newsletter")

    def test_signup_stores_the_address(self):
        response = self.client.post(self.url, {"email": "new@example.com"})

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            NewsletterSubscriber.objects.filter(email="new@example.com").exists()
        )

    def test_signing_up_twice_does_not_duplicate(self):
        self.client.post(self.url, {"email": "twice@example.com"})
        self.client.post(self.url, {"email": "twice@example.com"})

        self.assertEqual(
            NewsletterSubscriber.objects.filter(email="twice@example.com").count(), 1
        )

    def test_invalid_addresses_are_not_stored(self):
        self.client.post(self.url, {"email": "not-an-email"})

        self.assertFalse(NewsletterSubscriber.objects.exists())


class ContactTests(TestCase):
    url = reverse("core:contact")

    def test_page_renders(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_a_message_is_saved(self):
        response = self.client.post(
            self.url,
            {
                "name": "Rohan Mehta",
                "email": "rohan@example.com",
                "phone": "+91 9812345678",
                "topic": "trip",
                "message": "Do you run the Ladakh trip in September?",
            },
        )

        self.assertEqual(response.status_code, 302)
        message = ContactMessage.objects.get()
        self.assertEqual(message.name, "Rohan Mehta")
        self.assertEqual(message.topic, "trip")
        self.assertFalse(message.is_resolved)

    def test_an_incomplete_form_is_redisplayed(self):
        response = self.client.post(self.url, {"name": "Rohan"})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ContactMessage.objects.exists())


class StaffDashboardTests(TestCase):
    def setUp(self):
        self.package = make_package(price="10000")
        self.traveller = make_user(username="traveller")
        booking = make_booking(user=self.traveller, package=self.package)
        booking.mark_paid()
        make_booking(user=self.traveller, package=make_package(title="Second Trip"))

    def test_anonymous_visitors_are_redirected(self):
        response = self.client.get(reverse("dashboard:index"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_ordinary_travellers_are_kept_out(self):
        self.client.login(username="traveller", password="Tr@vello-2026")

        response = self.client.get(reverse("dashboard:index"))

        self.assertIn(response.status_code, (302, 403))

    def test_staff_see_the_analytics(self):
        make_user(username="staffer", is_staff=True)
        self.client.login(username="staffer", password="Tr@vello-2026")

        response = self.client.get(reverse("dashboard:index"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/index.html")
        kpis = response.context["kpis"]
        self.assertEqual(kpis["bookings_total"], 2)
        # Only the paid booking counts toward revenue.
        paid = Booking.objects.get(payment_status=Booking.PAYMENT_PAID)
        self.assertEqual(kpis["revenue_total"], paid.total_amount)
        self.assertEqual(kpis["pending"], 1)

    def test_things_needing_attention_are_counted(self):
        make_user(username="watcher", is_staff=True)
        self.client.login(username="watcher", password="Tr@vello-2026")

        response = self.client.get(reverse("dashboard:index"))

        attention = response.context["needs_attention"]
        self.assertEqual(attention["awaiting_payment"], 1)
        self.assertEqual(attention["unapproved_reviews"], 0)

    def test_chart_payloads_are_valid_json(self):
        make_user(username="chartstaff", is_staff=True)
        self.client.login(username="chartstaff", password="Tr@vello-2026")

        response = self.client.get(reverse("dashboard:index"))

        for key in (
            "chart_months",
            "chart_revenue",
            "chart_bookings",
            "chart_status_labels",
            "chart_status_values",
            "chart_destination_labels",
            "chart_destination_values",
        ):
            with self.subTest(key=key):
                self.assertIsInstance(json.loads(response.context[key]), list)


class AdminAccessTests(TestCase):
    def test_admin_login_page_is_branded(self):
        response = self.client.get("/admin/login/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Travello")

    def test_staff_reach_the_admin_index(self):
        make_user(username="root", is_staff=True, is_superuser=True)
        self.client.login(username="root", password="Tr@vello-2026")

        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 200)
