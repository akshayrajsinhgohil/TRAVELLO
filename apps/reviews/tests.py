"""Review tests: submission, moderation gate, verified badge and ownership."""

from django.test import TestCase
from django.urls import reverse

from apps.bookings.models import Booking
from apps.core.test_factories import make_booking, make_package, make_user

from .forms import ReviewForm
from .models import Review

GOOD_COMMENT = "Genuinely one of the better trips I've taken in the last few years."


class ReviewSubmissionTests(TestCase):
    def setUp(self):
        self.user = make_user(username="aanya")
        self.package = make_package(title="Reviewable Trip")
        self.client.login(username="aanya", password="Tr@vello-2026")
        self.url = reverse("reviews:submit", kwargs={"slug": self.package.slug})

    def _payload(self, **overrides):
        payload = {"rating": 5, "title": "Worth it", "comment": GOOD_COMMENT}
        payload.update(overrides)
        return payload

    def test_review_is_created_but_held_for_moderation(self):
        response = self.client.post(self.url, self._payload())

        self.assertRedirects(response, self.package.get_absolute_url())
        review = Review.objects.get()
        self.assertEqual(review.user, self.user)
        self.assertEqual(review.rating, 5)
        self.assertFalse(review.is_approved)

    def test_unapproved_reviews_do_not_move_the_average(self):
        self.client.post(self.url, self._payload())

        self.assertIsNone(self.package.average_rating)
        self.assertEqual(self.package.review_total, 0)

    def test_approving_publishes_it(self):
        self.client.post(self.url, self._payload())
        Review.objects.update(is_approved=True)

        self.assertEqual(self.package.average_rating, 5.0)
        self.assertEqual(self.package.review_total, 1)

    def test_a_paid_booking_marks_the_review_verified(self):
        booking = make_booking(user=self.user, package=self.package)
        booking.mark_paid()

        self.client.post(self.url, self._payload())

        review = Review.objects.get()
        self.assertEqual(review.booking, booking)
        self.assertTrue(review.is_verified)

    def test_without_a_paid_booking_the_review_is_unverified(self):
        make_booking(user=self.user, package=self.package)  # still unpaid

        self.client.post(self.url, self._payload())

        self.assertFalse(Review.objects.get().is_verified)

    def test_one_review_per_traveller_per_trip(self):
        self.client.post(self.url, self._payload())
        self.client.post(self.url, self._payload(title="Second go"))

        self.assertEqual(Review.objects.filter(package=self.package).count(), 1)

    def test_short_comments_are_rejected(self):
        self.client.post(self.url, self._payload(comment="Nice."))

        self.assertFalse(Review.objects.exists())

    def test_anonymous_visitors_are_sent_to_login(self):
        self.client.logout()

        response = self.client.post(self.url, self._payload())

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)
        self.assertFalse(Review.objects.exists())

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)


class ReviewDeletionTests(TestCase):
    def setUp(self):
        self.author = make_user(username="author")
        self.package = make_package()
        self.review = Review.objects.create(
            package=self.package, user=self.author, rating=4,
            title="Mine", comment=GOOD_COMMENT, is_approved=True,
        )

    def test_the_author_can_delete_their_own(self):
        self.client.login(username="author", password="Tr@vello-2026")

        response = self.client.post(
            reverse("reviews:delete", kwargs={"pk": self.review.pk})
        )

        self.assertRedirects(response, self.package.get_absolute_url())
        self.assertFalse(Review.objects.exists())

    def test_nobody_else_can(self):
        make_user(username="stranger")
        self.client.login(username="stranger", password="Tr@vello-2026")

        response = self.client.post(
            reverse("reviews:delete", kwargs={"pk": self.review.pk})
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Review.objects.exists())


class ReviewFormTests(TestCase):
    def test_comment_length_floor(self):
        form = ReviewForm({"rating": 5, "title": "Good", "comment": "Too short"})
        self.assertFalse(form.is_valid())
        self.assertIn("comment", form.errors)

    def test_a_full_review_validates(self):
        form = ReviewForm({"rating": 4, "title": "Good", "comment": GOOD_COMMENT})
        self.assertTrue(form.is_valid())

    def test_rating_must_be_one_to_five(self):
        form = ReviewForm({"rating": 9, "title": "Nope", "comment": GOOD_COMMENT})
        self.assertFalse(form.is_valid())


class ReviewModelTests(TestCase):
    def test_star_string(self):
        review = Review(rating=3)
        self.assertEqual(review.star_string, "★★★☆☆")

    def test_deleting_a_booking_keeps_the_review(self):
        user = make_user("keeper")
        package = make_package()
        booking = make_booking(user=user, package=package)
        review = Review.objects.create(
            package=package, user=user, booking=booking, rating=5,
            title="Kept", comment=GOOD_COMMENT,
        )

        Booking.objects.filter(pk=booking.pk).delete()
        review.refresh_from_db()

        self.assertIsNone(review.booking)
        self.assertFalse(review.is_verified)
