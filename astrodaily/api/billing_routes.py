"""Plans, a person's subscription, and buying one."""
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth.deps import get_current_user
from ..billing import service
from ..billing.plans import PLANS
from ..billing.verify import BillingNotConfigured, InvalidPurchase, get_verifier, utc_now
from ..config import get_settings
from ..db import get_db
from ..models import User
from ..ratelimit import limit

router = APIRouter(tags=["billing"], dependencies=[Depends(limit("me", "rate_limit_default_per_minute"))])


class PlanOut(BaseModel):
    id: str
    period_days: int
    price_inr: int
    trial_days: int


class PlansOut(BaseModel):
    provider: str  # "none" (nothing on sale), "fake" (test store) or "google"
    plans: list[PlanOut]


class SubscriptionOut(BaseModel):
    premium: bool
    plan: str | None = None
    expires_at: datetime | None = None
    auto_renewing: bool = False  # false once cancelled: access runs to expires_at and then ends
    trial: bool = False
    provider: str


class PurchaseIn(BaseModel):
    product_id: Literal["monthly", "yearly"]
    purchase_token: str = Field(min_length=8, max_length=512)


def subscription_out(user: User) -> SubscriptionOut:
    sub = service.current(user)
    provider = get_settings().billing_provider
    if sub is None:
        return SubscriptionOut(premium=False, provider=provider)
    return SubscriptionOut(premium=True, plan=sub.product_id, expires_at=service.aware(sub.expires_at),
                           auto_renewing=sub.auto_renewing, trial=sub.trial, provider=provider)


@router.get("/v1/plans", response_model=PlansOut)
def plans() -> PlansOut:
    return PlansOut(provider=get_settings().billing_provider,
                    plans=[PlanOut(id=p.id, period_days=p.period_days, price_inr=p.price_inr, trial_days=p.trial_days)
                           for p in PLANS.values()])


@router.get("/v1/me/subscription", response_model=SubscriptionOut)
def my_subscription(user: User = Depends(get_current_user)) -> SubscriptionOut:
    return subscription_out(user)


@router.post("/v1/me/subscription", response_model=SubscriptionOut)
def buy(body: PurchaseIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SubscriptionOut:
    """Hand over the store's purchase token. The server checks it with the store; the app's word is not enough."""
    try:
        verifier = get_verifier()
    except BillingNotConfigured:
        raise HTTPException(status_code=503, detail="Purchases are not available yet.")
    try:
        info = verifier.verify(body.product_id, body.purchase_token, utc_now())
    except InvalidPurchase:
        raise HTTPException(status_code=422, detail="That purchase could not be verified.")
    try:
        service.record_purchase(db, user, info, body.purchase_token, verifier.name)
    except service.TokenBelongsToSomeoneElse:
        raise HTTPException(status_code=409, detail="That purchase belongs to another account.")
    return subscription_out(user)


def _fake_only() -> None:
    if get_settings().billing_provider != "fake":
        raise HTTPException(status_code=404, detail="Not found")


@router.post("/v1/me/subscription/fake/cancel", response_model=SubscriptionOut)
def fake_cancel(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SubscriptionOut:
    """Test store only. Like cancelling in Google Play: it stops renewing, access runs to the end of the period."""
    _fake_only()
    sub = service.current(user)
    if sub is None:
        raise HTTPException(status_code=404, detail="No active subscription")
    sub.auto_renewing = False
    db.commit()
    return subscription_out(user)


@router.post("/v1/me/subscription/fake/expire", response_model=SubscriptionOut)
def fake_expire(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SubscriptionOut:
    """Test store only. Ends the subscription now, as if the period had run out."""
    _fake_only()
    for sub in user.subscriptions:
        sub.expires_at = min(service.aware(sub.expires_at), utc_now())
        sub.auto_renewing = False
    db.commit()
    return subscription_out(user)
