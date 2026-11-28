"""The plans on sale. Prices here are what the app shows with the fake store; with Google Play the store's own
(localised) price is shown, and these stay the record of what was agreed."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Plan:
    id: str
    period_days: int
    price_inr: int
    trial_days: int


PLANS: dict[str, Plan] = {
    "monthly": Plan("monthly", 30, 49, 7),
    "yearly": Plan("yearly", 365, 399, 7),
}
