"""Payment gateway adapters.

Travello talks to one small interface, so swapping Razorpay for Stripe (or the
built-in sandbox) is a settings change, not a code change.

    gateway = get_gateway()
    order = gateway.create_order(booking)
    gateway.verify(payload)  -> bool
"""

import logging
import secrets
from decimal import Decimal

from django.conf import settings

logger = logging.getLogger(__name__)


class BaseGateway:
    name = "base"

    def create_order(self, booking) -> dict:
        raise NotImplementedError

    def verify(self, payload: dict) -> bool:
        raise NotImplementedError

    @staticmethod
    def to_minor_units(amount: Decimal) -> int:
        """Gateways bill in paise/cents."""
        return int(Decimal(amount) * 100)


class SandboxGateway(BaseGateway):
    """Simulates a gateway so the booking flow works with no account or keys.

    This is the default in development. It never touches the network.
    """

    name = "sandbox"

    def create_order(self, booking) -> dict:
        return {
            "gateway": self.name,
            "order_id": f"sandbox_{secrets.token_hex(8)}",
            "amount": self.to_minor_units(booking.total_amount),
            "currency": settings.CURRENCY,
            "key": "sandbox",
        }

    def verify(self, payload: dict) -> bool:
        # In sandbox mode any callback carrying the order id is accepted.
        return bool(payload.get("order_id"))


class RazorpayGateway(BaseGateway):
    name = "razorpay"

    def __init__(self):
        import razorpay  # imported lazily so the package stays optional

        self.client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

    def create_order(self, booking) -> dict:
        order = self.client.order.create(
            {
                "amount": self.to_minor_units(booking.total_amount),
                "currency": settings.CURRENCY,
                "receipt": booking.reference,
                "notes": {"trip": booking.package.title, "guests": str(booking.guests)},
            }
        )
        return {
            "gateway": self.name,
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
            "key": settings.RAZORPAY_KEY_ID,
        }

    def verify(self, payload: dict) -> bool:
        try:
            self.client.utility.verify_payment_signature(
                {
                    "razorpay_order_id": payload["order_id"],
                    "razorpay_payment_id": payload["payment_id"],
                    "razorpay_signature": payload["signature"],
                }
            )
            return True
        except Exception as exc:  # razorpay raises SignatureVerificationError
            logger.warning("Razorpay signature check failed: %s", exc)
            return False


class StripeGateway(BaseGateway):
    name = "stripe"

    def __init__(self):
        import stripe

        stripe.api_key = settings.STRIPE_SECRET_KEY
        self.stripe = stripe

    def create_order(self, booking) -> dict:
        intent = self.stripe.PaymentIntent.create(
            amount=self.to_minor_units(booking.total_amount),
            currency=settings.CURRENCY.lower(),
            metadata={"reference": booking.reference},
            automatic_payment_methods={"enabled": True},
        )
        return {
            "gateway": self.name,
            "order_id": intent.id,
            "client_secret": intent.client_secret,
            "amount": intent.amount,
            "currency": intent.currency,
            "key": settings.STRIPE_PUBLIC_KEY,
        }

    def verify(self, payload: dict) -> bool:
        try:
            intent = self.stripe.PaymentIntent.retrieve(payload["order_id"])
            return intent.status == "succeeded"
        except Exception as exc:
            logger.warning("Stripe verification failed: %s", exc)
            return False


GATEWAYS = {
    "sandbox": SandboxGateway,
    "razorpay": RazorpayGateway,
    "stripe": StripeGateway,
}


def get_gateway() -> BaseGateway:
    """Return the configured gateway, falling back to sandbox if keys are missing."""
    choice = (settings.PAYMENT_GATEWAY or "sandbox").lower()
    if choice == "razorpay" and not settings.RAZORPAY_KEY_ID:
        logger.warning("Razorpay selected but no keys found — using the sandbox gateway.")
        choice = "sandbox"
    if choice == "stripe" and not settings.STRIPE_SECRET_KEY:
        logger.warning("Stripe selected but no keys found — using the sandbox gateway.")
        choice = "sandbox"
    try:
        return GATEWAYS.get(choice, SandboxGateway)()
    except ImportError:
        logger.warning("%s SDK is not installed — using the sandbox gateway.", choice)
        return SandboxGateway()
