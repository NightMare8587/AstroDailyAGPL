"""Who is premium, and recording a purchase."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Subscription, User
from .verify import PurchaseInfo, utc_now


def aware(moment: datetime) -> datetime:
    """SQLite hands back dates without a zone; everything here is UTC."""
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)


def current(user: User, now: datetime | None = None) -> Subscription | None:
    """The subscription that gives access right now: not revoked, not expired; the one that lasts longest."""
    now = now or utc_now()
    live = [s for s in user.subscriptions if s.revoked_at is None and aware(s.expires_at) > now]
    return max(live, key=lambda s: s.expires_at, default=None)


def is_premium(user: User | None, now: datetime | None = None) -> bool:
    return user is not None and current(user, now) is not None


def chat_limit(user: User) -> int:
    """User messages allowed per rolling 24 hours: more for paying users."""
    from ..config import get_settings
    s = get_settings()
    return s.chat_daily_message_limit if is_premium(user) else s.chat_free_daily_message_limit


class TokenBelongsToSomeoneElse(Exception):
    pass


def record_purchase(db: Session, user: User, info: PurchaseInfo, token: str, source: str) -> Subscription:
    """Save a verified purchase. The same token again just refreshes it; a token already used by another account is refused."""
    row = db.scalar(select(Subscription).where(Subscription.purchase_token == token))
    if row is not None and row.user_id != user.id:
        raise TokenBelongsToSomeoneElse
    if row is None:
        row = Subscription(user_id=user.id, product_id=info.product_id, source=source, purchase_token=token,
                           expires_at=info.expires_at, auto_renewing=info.auto_renewing, trial=info.trial)
        db.add(row)
    else:
        row.expires_at, row.auto_renewing, row.trial = info.expires_at, info.auto_renewing, info.trial
    db.commit()
    db.refresh(user)
    return row
