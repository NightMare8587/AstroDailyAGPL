from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from ..auth.deps import get_current_user
from ..db import get_db
from ..models import Place, User, utcnow
from ..ratelimit import limit
from .schemas import UserOut

router = APIRouter(prefix="/v1/me", tags=["me"],
                   dependencies=[Depends(limit("me", "rate_limit_default_per_minute"))])


class UserUpdate(BaseModel):
    language: Literal["en", "hi"] | None = None
    # Version string of the privacy policy the user accepted; recording it stores the consent time.
    consent_version: str | None = Field(default=None, min_length=1, max_length=32)
    # Home city from /v1/places/search. Send null to clear it; leave it out to keep the current one.
    home_place_id: int | None = None
    # The setup page after sign-in. Names are trimmed and must not be blank; gender is optional (null clears it).
    first_name: str | None = Field(default=None, max_length=40)
    last_name: str | None = Field(default=None, max_length=40)
    date_of_birth: date | None = None
    gender: Literal["female", "male", "other"] | None = None

    @field_validator("first_name", "last_name")
    @classmethod
    def _name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = " ".join(v.split())
        if not v:
            raise ValueError("must not be blank")
        return v

    @field_validator("date_of_birth")
    @classmethod
    def _dob(cls, v: date | None) -> date | None:
        if v is not None and not (date(1900, 1, 1) <= v <= date.today()):
            raise ValueError("date of birth must be between 1900 and today")
        return v


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
    # first name, last name and date of birth can be changed but not cleared (the account needs them).
    if body.first_name is not None:
        user.first_name = body.first_name
    if body.last_name is not None:
        user.last_name = body.last_name
    if body.date_of_birth is not None:
        user.date_of_birth = body.date_of_birth
    if "gender" in body.model_fields_set:
        user.gender = body.gender
    if "home_place_id" in body.model_fields_set:
        if body.home_place_id is None:
            user.home_place = None
        else:
            place = db.get(Place, body.home_place_id)
            if place is None:
                raise HTTPException(status_code=422, detail="Unknown place")
            user.home_place = place
    db.commit()
    return UserOut.from_user(user)


@router.delete("", status_code=204)
def delete_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    """Permanently delete the account and everything attached to it."""
    db.delete(user)
    db.commit()
