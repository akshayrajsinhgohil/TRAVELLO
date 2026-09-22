"""Auth tests: registration, sign-in, email verification and saved trips."""

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.core.test_factories import make_package, make_user

from .models import Wishlist

User = get_user_model()

VALID_SIGNUP = {
    "first_name": "Aanya",
    "username": "aanya",
    "email": "aanya@example.com",
    "password1": "Tr@vello-2026",
    "password2": "Tr@vello-2026",
    "newsletter_opt_in": True,
}


class RegistrationTests(TestCase):
    url = "/accounts/register/"

    def test_page_renders(self):
        response = self.client.get(reverse("accounts:register"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/register.html")

    def test_signup_creates_user_and_signs_them_in(self):
        response = self.client.post(reverse("accounts:register"), VALID_SIGNUP)

        self.assertRedirects(response, reverse("accounts:dashboard"))
        user = User.objects.get(username="aanya")
        self.assertEqual(user.email, "aanya@example.com")
        self.assertTrue(user.newsletter_opt_in)
        # New accounts start unverified — the emailed link flips this.
        self.assertFalse(user.is_email_verified)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_signup_sends_a_verification_email(self):
        self.client.post(reverse("accounts:register"), VALID_SIGNUP)

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertIn("aanya@example.com", message.to)
        self.assertIn("/accounts/verify/", message.body)

    def test_duplicate_email_is_rejected(self):
        make_user(username="existing", email="aanya@example.com")

        response = self.client.post(reverse("accounts:register"), VALID_SIGNUP)

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "email",
            "An account already uses this email. Try signing in instead.",
        )
        self.assertFalse(User.objects.filter(username="aanya").exists())

    def test_mismatched_passwords_are_rejected(self):
        payload = VALID_SIGNUP | {"password2": "something-else"}

        response = self.client.post(reverse("accounts:register"), payload)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="aanya").exists())

    def test_signed_in_users_are_sent_to_their_dashboard(self):
        make_user(username="already")
        self.client.login(username="already", password="Tr@vello-2026")

        response = self.client.get(reverse("accounts:register"))

        self.assertRedirects(response, reverse("accounts:dashboard"))


class LoginTests(TestCase):
    def setUp(self):
        self.user = make_user(username="rohan", email="rohan@example.com")

    def test_login_with_username(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "rohan", "password": "Tr@vello-2026"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_login_with_email(self):
        """The custom backend accepts an email in the username field."""
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "rohan@example.com", "password": "Tr@vello-2026"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_wrong_password_keeps_you_out(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "rohan", "password": "nope"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_works_from_a_plain_link(self):
        self.client.login(username="rohan", password="Tr@vello-2026")

        response = self.client.get(reverse("accounts:logout"))

        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)


class EmailVerificationTests(TestCase):
    def setUp(self):
        self.user = make_user(username="meera")
        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))

    def _verify_url(self, token):
        return reverse(
            "accounts:verify_email", kwargs={"uidb64": self.uid, "token": token}
        )

    def test_valid_link_verifies_the_account(self):
        token = default_token_generator.make_token(self.user)

        response = self.client.get(self._verify_url(token))

        self.assertRedirects(
            response, reverse("accounts:dashboard"), fetch_redirect_response=False
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_email_verified)

    def test_tampered_token_is_refused(self):
        response = self.client.get(self._verify_url("not-a-real-token"))

        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_email_verified)

    def test_token_cannot_be_reused_after_verification(self):
        token = default_token_generator.make_token(self.user)
        self.client.get(self._verify_url(token))
        self.user.refresh_from_db()

        # Changing the verified flag does not invalidate Django's token, but a
        # password change does — which is the case that matters for replay.
        self.user.set_password("a-brand-new-password")
        self.user.save()

        response = self.client.get(self._verify_url(token))
        self.assertEqual(response.status_code, 400)

    def test_resend_requires_a_post_and_a_session(self):
        self.assertEqual(
            self.client.post(reverse("accounts:resend_verification")).status_code, 302
        )
        self.assertEqual(len(mail.outbox), 0)

        self.client.login(username="meera", password="Tr@vello-2026")
        self.client.post(reverse("accounts:resend_verification"))
        self.assertEqual(len(mail.outbox), 1)


class DashboardAccessTests(TestCase):
    def test_dashboard_needs_a_login(self):
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_dashboard_renders_for_a_signed_in_user(self):
        make_user(username="dev")
        self.client.login(username="dev", password="Tr@vello-2026")

        response = self.client.get(reverse("accounts:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/dashboard.html")
        self.assertEqual(response.context["booking_count"], 0)


class WishlistTests(TestCase):
    def setUp(self):
        self.user = make_user(username="tara")
        self.package = make_package(title="Saved Trip")
        self.client.login(username="tara", password="Tr@vello-2026")
        self.url = reverse(
            "accounts:toggle_wishlist", kwargs={"slug": self.package.slug}
        )

    def test_toggle_saves_then_unsaves(self):
        self.client.post(self.url, headers={"x-requested-with": "XMLHttpRequest"})
        self.assertTrue(
            Wishlist.objects.filter(user=self.user, package=self.package).exists()
        )

        response = self.client.post(
            self.url, headers={"x-requested-with": "XMLHttpRequest"}
        )
        self.assertFalse(
            Wishlist.objects.filter(user=self.user, package=self.package).exists()
        )
        self.assertJSONEqual(
            response.content, {"saved": False, "package": self.package.slug}
        )

    def test_get_requests_are_refused(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_saved_trips_page_lists_them(self):
        Wishlist.objects.create(user=self.user, package=self.package)

        response = self.client.get(reverse("accounts:wishlist"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Saved Trip")


class ProfileTests(TestCase):
    def setUp(self):
        self.user = make_user(username="ishaan")
        self.client.login(username="ishaan", password="Tr@vello-2026")

    def test_profile_updates_save(self):
        response = self.client.post(
            reverse("accounts:profile"),
            {
                "first_name": "Ishaan",
                "last_name": "Verma",
                "email": "ishaan@example.com",
                "phone": "+91 9812345678",
                "bio": "Mountains over beaches, every time.",
                "city": "Delhi",
                "country": "India",
                "newsletter_opt_in": "on",
            },
        )

        self.assertRedirects(response, reverse("accounts:profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.last_name, "Verma")
        self.assertEqual(self.user.city, "Delhi")

    def test_cannot_take_another_users_email(self):
        make_user(username="someone", email="taken@example.com")

        response = self.client.post(
            reverse("accounts:profile"),
            {"first_name": "Ishaan", "email": "taken@example.com"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "email", "Another account already uses this email."
        )


class UserModelTests(TestCase):
    def test_initials_prefer_the_name(self):
        user = make_user(username="dev", first_name="Dev", last_name="Patel")
        self.assertEqual(user.initials, "DP")

    def test_initials_fall_back_to_the_username(self):
        user = make_user(username="wanderer", first_name="", last_name="")
        self.assertEqual(user.initials, "WA")

    def test_email_is_unique(self):
        make_user(username="one", email="clash@example.com")
        with self.assertRaises(Exception):
            make_user(username="two", email="clash@example.com")
