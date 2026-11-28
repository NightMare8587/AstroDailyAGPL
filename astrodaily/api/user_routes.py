from datetime import date, timedelta
from datetime import time as time_type
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from ..auth.deps import get_current_user
from ..db import get_db
from ..config import get_settings
from ..models import BirthProfile, Place, User, utcnow
from ..ratelimit import limit
from .birth import check_date, place_label, resolve_location
from ..horoscope import daily_text, love_reading, match_summary, planet_cards
from .profile_routes import settle_moon_sign
from .schemas import UserOut
from sqlalchemy import func, select

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
        # One day of slack: this server runs on UTC, and in India the date is already tomorrow until 05:30.
        if v is not None and not (date(1900, 1, 1) <= v <= date.today() + timedelta(days=1)):
            raise ValueError("date of birth must be between 1900 and today")
        return v


@router.get("", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.from_user(user)


def _apply_user_update(body: UserUpdate, user: User, db: Session) -> None:
    """Change only the fields that were sent. Shared by PATCH /v1/me and POST /v1/me/setup."""
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


@router.patch("", response_model=UserOut)
def update_me(body: UserUpdate, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)) -> UserOut:
    _apply_user_update(body, user, db)
    db.commit()
    return UserOut.from_user(user)


class SetupIn(UserUpdate):
    """The setup page after sign-in, saved in one step: the account details and the person's own birth profile.

    first_name, last_name, date_of_birth and birth_place_id are required. consent_version is required the first time
    (when the person has not agreed yet). birth_time is null when the person does not know it."""
    first_name: str = Field(max_length=40)
    last_name: str = Field(max_length=40)
    date_of_birth: date
    birth_place_id: int
    birth_time: time_type | None = None
    # Only needed when the time is unknown and the Moon changed sign on the birth date (see POST /v1/moon-sign).
    moon_sign: int | None = Field(default=None, ge=1, le=12)


@router.post("/setup", response_model=UserOut)
def setup(body: SetupIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserOut:
    """Save the setup page all at once, or not at all: consent, details, and the "Me" birth profile."""
    if user.consented_at is None and body.consent_version is None:
        raise HTTPException(status_code=422, detail="consent_version is required the first time")
    check_date("date_of_birth", body.date_of_birth)
    place = db.get(Place, body.birth_place_id)
    if place is None:
        raise HTTPException(status_code=422, detail="Unknown birth place")
    _apply_user_update(body, user, db)
    # The person's own profile is the oldest one, labelled "Me". Setting up again updates it.
    mine = next((p for p in user.profiles if p.label == "Me"), None)
    if mine is None:
        count = db.scalar(select(func.count()).select_from(BirthProfile).where(BirthProfile.user_id == user.id))
        if count >= get_settings().max_profiles_per_user:
            raise HTTPException(status_code=409, detail="Profile limit reached. Delete one first.")
        mine = BirthProfile(user_id=user.id, label="Me")
        db.add(mine)
    loc = resolve_location(db, place.id, None, None, None)
    if mine.place_id != place.id:
        mine.utc_offset_minutes = None  # an explicit UTC offset belongs to the old place; keep it only when the place is the same
    before = (mine.birth_date, mine.birth_time, mine.place_id)
    mine.birth_date, mine.birth_time = body.date_of_birth, body.birth_time
    mine.place_id, mine.place_name = place.id, place_label(place)
    mine.latitude, mine.longitude, mine.timezone = loc.latitude, loc.longitude, loc.timezone
    settle_moon_sign(mine, body.moon_sign)
    if before != (mine.birth_date, mine.birth_time, mine.place_id):
        daily_text.forget(db, mine)  # written from the old details
        love_reading.forget(db, mine)
        planet_cards.forget(db, mine)
        match_summary.forget(db, mine)
    db.commit()
    db.refresh(user)
    return UserOut.from_user(user)


@router.delete("", status_code=204)
def delete_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    """Permanently delete the account and everything attached to it."""
    db.delete(user)
    db.commit()
