"""Checking a purchase with the store. The server never trusts the app's word that someone paid: it asks the store.

``none``  no store configured: purchases are refused (the default, and what production runs until Google Play is set up).
``fake``  a stand-in store for building and testing the whole flow. A purchase token that says what it is
          (``fake:<plan>:<state>:<anything>``) is believed. Anyone can make one, so this must never be on in production
          with real users.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

from ..config import get_settings
from .plans import PLANS


class BillingNotConfigured(Exception):
    pass


class InvalidPurchase(Exception):
    pass


@dataclass(frozen=True)
class PurchaseInfo:
    product_id: str
    expires_at: datetime
    auto_renewing: bool
    trial: bool


class Verifier(Protocol):
    name: str

    def verify(self, product_id: str, purchase_token: str, now: datetime) -> PurchaseInfo: ...


class FakeVerifier:
    name = "fake"
    STATES = ("trial", "paid")

    def verify(self, product_id: str, purchase_token: str, now: datetime) -> PurchaseInfo:
        parts = purchase_token.split(":", 3)
        if len(parts) != 4 or parts[0] != "fake" or parts[1] != product_id or parts[2] not in self.STATES:
            raise InvalidPurchase("not a fake-store purchase for this plan")
        plan = PLANS[product_id]
        days = plan.trial_days if parts[2] == "trial" else plan.period_days
        return PurchaseInfo(product_id, now + timedelta(days=days), True, parts[2] == "trial")


def get_verifier() -> Verifier:
    provider = get_settings().billing_provider
    if provider == "fake":
        return FakeVerifier()
    raise BillingNotConfigured


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
