"""Saved birth profiles: the user's own and family members'. Personal data, so every endpoint needs a
signed-in user who has recorded consent, and only the owner can see a profile."""
import uuid
from datetime import date as date_type
from datetime import datetime
from datetime import time as time_type
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth.deps import get_current_user
from ..config import get_settings
from ..db import get_db
from ..models import BirthProfile, Place, User
from ..ratelimit import limit
from .birth import Location, check_date, resolve_location
from .kundli_routes import KundliOut, build_kundli
from .schemas import UserOut


def require_consent(user: User = Depends(get_current_user)) -> User:
    """Birth details are personal data: refuse until the user has accepted the privacy policy."""
    if user.consented_at is None:
        raise HTTPException(status_code=403, detail="Consent required: accept the privacy policy first "
                                                    "(PATCH /v1/me with consent_version).")
    return user


router = APIRouter(prefix="/v1/profiles", tags=["profiles"],
                   dependencies=[Depends(limit("profiles", "rate_limit_default_per_minute"))])


class ProfileIn(BaseModel):
    label: str = Field("Me", min_length=1, max_length=40, description="Who this is, e.g. Me, Mom")
    birth_date: date_type
    birth_time: time_type
    place_id: int | None = None
    lat: float | None = Field(None, ge=-66.0, le=66.0)
    lon: float | None = Field(None, ge=-180.0, le=180.0)
    tz: str | None = None
    utc_offset_minutes: int | None = Field(None, ge=-840, le=840)


class ProfileUpdate(BaseModel):
    """Only the fields you send change. Changing the place needs place_id, or lat and lon."""
    label: str | None = Field(None, min_length=1, max_length=40)
    birth_date: date_type | None = None
    birth_time: time_type | None = None
    place_id: int | None = None
    lat: float | None = Field(None, ge=-66.0, le=66.0)
    lon: float | None = Field(None, ge=-180.0, le=180.0)
    tz: str | None = None
    utc_offset_minutes: int | None = Field(None, ge=-840, le=840)  # send null to clear


class ProfileOut(BaseModel):
    id: uuid.UUID
    label: str
    birth_date: date_type
    birth_time: time_type
    place_id: int | None
    place_name: str | None
    latitude: float
    longitude: float
    timezone: str
    utc_offset_minutes: int | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_profile(cls, p: BirthProfile) -> "ProfileOut":
        return cls(id=p.id, label=p.label, birth_date=p.birth_date, birth_time=p.birth_time, place_id=p.place_id,
                   place_name=p.place_name, latitude=p.latitude, longitude=p.longitude, timezone=p.timezone,
                   utc_offset_minutes=p.utc_offset_minutes, created_at=p.created_at, updated_at=p.updated_at)


def _place_label(place: Place | None) -> str | None:
    if place is None:
        return None
    return ", ".join(x for x in (place.name, place.district, place.state) if x)


def _apply_location(profile: BirthProfile, loc: Location) -> None:
    profile.place_id = loc.place.id if loc.place else None
    profile.place_name = _place_label(loc.place)
    profile.latitude, profile.longitude, profile.timezone = loc.latitude, loc.longitude, loc.timezone


def _own_profile(db: Session, user: User, profile_id: uuid.UUID) -> BirthProfile:
    profile = db.get(BirthProfile, profile_id)
    # Someone else's profile looks exactly like one that does not exist.
    if profile is None or profile.user_id != user.id:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.post("", response_model=ProfileOut, status_code=201)
def create_profile(body: ProfileIn, user: User = Depends(require_consent), db: Session = Depends(get_db)) -> ProfileOut:
    check_date("birth_date", body.birth_date)
    count = db.scalar(select(func.count()).select_from(BirthProfile).where(BirthProfile.user_id == user.id))
    if count >= get_settings().max_profiles_per_user:
        raise HTTPException(status_code=409, detail="Profile limit reached. Delete one first.")
    loc = resolve_location(db, body.place_id, body.lat, body.lon, body.tz)
    profile = BirthProfile(user_id=user.id, label=body.label, birth_date=body.birth_date,
                           birth_time=body.birth_time, utc_offset_minutes=body.utc_offset_minutes)
    _apply_location(profile, loc)
    db.add(profile)
    db.commit()
    return ProfileOut.from_profile(profile)


@router.get("", response_model=list[ProfileOut])
def list_profiles(user: User = Depends(require_consent)) -> list[ProfileOut]:
    return [ProfileOut.from_profile(p) for p in user.profiles]


@router.get("/{profile_id}", response_model=ProfileOut)
def get_profile(profile_id: uuid.UUID, user: User = Depends(require_consent), db: Session = Depends(get_db)) -> ProfileOut:
    return ProfileOut.from_profile(_own_profile(db, user, profile_id))


@router.patch("/{profile_id}", response_model=ProfileOut)
def update_profile(profile_id: uuid.UUID, body: ProfileUpdate, user: User = Depends(require_consent),
                   db: Session = Depends(get_db)) -> ProfileOut:
    profile = _own_profile(db, user, profile_id)
    sent = body.model_fields_set
    if "label" in sent and body.label is not None:
        profile.label = body.label
    if "birth_date" in sent and body.birth_date is not None:
        check_date("birth_date", body.birth_date)
        profile.birth_date = body.birth_date
    if "birth_time" in sent and body.birth_time is not None:
        profile.birth_time = body.birth_time
    if sent & {"place_id", "lat", "lon", "tz"}:
        _apply_location(profile, resolve_location(db, body.place_id, body.lat, body.lon, body.tz))
    if "utc_offset_minutes" in sent:
        profile.utc_offset_minutes = body.utc_offset_minutes
    db.commit()
    return ProfileOut.from_profile(profile)


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: uuid.UUID, user: User = Depends(require_consent), db: Session = Depends(get_db)) -> None:
    db.delete(_own_profile(db, user, profile_id))
    db.commit()


@router.get("/{profile_id}/kundli", response_model=KundliOut)
def profile_kundli(
    profile_id: uuid.UUID,
    node: Literal["mean", "true"] = "mean",
    as_of: date_type | None = None,
    user: User = Depends(require_consent),
    db: Session = Depends(get_db),
) -> KundliOut:
    """The chart for a saved profile. Birth details stay on the server and out of the URL."""
    p = _own_profile(db, user, profile_id)
    if as_of is not None:
        check_date("as_of", as_of)
    place = db.get(Place, p.place_id) if p.place_id else None
    location = Location(p.latitude, p.longitude, p.timezone, place)
    return build_kundli(birth_date=p.birth_date, birth_time=p.birth_time, location=location,
                        utc_offset_minutes=p.utc_offset_minutes, node=node, as_of_date=as_of)


export_router = APIRouter(prefix="/v1/me", tags=["me"],
                          dependencies=[Depends(limit("me", "rate_limit_default_per_minute"))])


class ExportOut(BaseModel):
    account: UserOut
    consented_at: datetime | None
    profiles: list[ProfileOut]


@export_router.get("/export", response_model=ExportOut)
def export_my_data(user: User = Depends(get_current_user)) -> ExportOut:
    """Everything we hold about the signed-in user, in one response."""
    return ExportOut(account=UserOut.from_user(user), consented_at=user.consented_at,
                     profiles=[ProfileOut.from_profile(p) for p in user.profiles])
