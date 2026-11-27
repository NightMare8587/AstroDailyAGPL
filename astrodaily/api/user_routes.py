from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth.deps import get_current_user
from ..db import get_db
from ..models import User, utcnow
from ..ratelimit import limit
from .schemas import UserOut

router = APIRouter(prefix="/v1/me", tags=["me"],
                   dependencies=[Depends(limit("me", "rate_limit_default_per_minute"))])


class UserUpdate(BaseModel):
    language: Literal["en", "hi"] | None = None
    # Version string of the privacy policy the user accepted; recording it stores the consent time.
    consent_version: str | None = Field(default=None, min_length=1, max_length=32)


@router.get("", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.from_user(user)


@router.patch("", response_model=UserOut)
def update_me(body: UserUpdate, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)) -> UserOut:
    if body.language is not None:
        user.language = body.language
    if body.consent_version is not None:
        user.consent_version = body.consent_version
        user.consented_at = utcnow()
    db.commit()
    return UserOut.from_user(user)


@router.delete("", status_code=204)
def delete_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    """Permanently delete the account and everything attached to it."""
    db.delete(user)
    db.commit()
