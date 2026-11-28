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
from ..calc import moonsign
from ..horoscope import daily_text, love_reading
from ..models import BirthProfile, Place, User
from ..ratelimit import limit
from .birth import Location, check_date, place_label as _place_label, resolve_location
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
    # Leave out (null) when the person does not know their birth time. Then the Moon sign comes from the date;
    # if the Moon changed sign that day, send the chosen one as moon_sign (see POST /v1/moon-sign).
    birth_time: time_type | None = None
    moon_sign: int | None = Field(None, ge=1, le=12)
    place_id: int | None = None
    lat: float | None = Field(None, ge=-66.0, le=66.0)
    lon: float | None = Field(None, ge=-180.0, le=180.0)
    tz: str | None = None
    utc_offset_minutes: int | None = Field(None, ge=-840, le=840)


class ProfileUpdate(BaseModel):
    """Only the fields you send change. Changing the place needs place_id, or lat and lon."""
    label: str | None = Field(None, min_length=1, max_length=40)
    birth_date: date_type | None = None
    birth_time: time_type | None = None  # send null to say the time is not known
    moon_sign: int | None = Field(None, ge=1, le=12)
    place_id: int | None = None
    lat: float | None = Field(None, ge=-66.0, le=66.0)
    lon: float | None = Field(None, ge=-180.0, le=180.0)
    tz: str | None = None
    utc_offset_minutes: int | None = Field(None, ge=-840, le=840)  # send null to clear


class ProfileOut(BaseModel):
    id: uuid.UUID
    label: str
    birth_date: date_type
    birth_time: time_type | None  # null when the birth time is not known
    time_known: bool
    moon_sign: int | None         # 1..12: worked out from the birth time, or chosen when the time is unknown
    nakshatra: int | None         # 1..27, only with a birth time
    pada: int | None
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
        sign, nak, pada = profile_moon(p)
        return cls(id=p.id, label=p.label, birth_date=p.birth_date, birth_time=p.birth_time,
                   time_known=p.birth_time is not None, moon_sign=sign, nakshatra=nak, pada=pada, place_id=p.place_id,
                   place_name=p.place_name, latitude=p.latitude, longitude=p.longitude, timezone=p.timezone,
                   utc_offset_minutes=p.utc_offset_minutes, created_at=p.created_at, updated_at=p.updated_at)


def profile_moon(p: BirthProfile) -> tuple[int | None, int | None, int | None]:
    """(Moon sign, nakshatra, pada). Worked out from the birth time when there is one, else the stored sign."""
    if p.birth_time is None:
        return p.moon_sign, None, None
    try:
        m = moonsign.moon_at_birth(p.birth_date, p.birth_time, p.timezone, p.utc_offset_minutes)
    except (ValueError, OverflowError):
        return None, None, None
    return m.sign, m.nakshatra, m.pada


def settle_moon_sign(p: BirthProfile, chosen: int | None) -> None:
    """Fill in the stored Moon sign for a profile without a birth time. With a time there is nothing to store.

    The Moon is in one sign all day on about half of dates: then it is that sign. Otherwise the person must pick one
    of the two possible signs, and anything else is refused with the two choices in the error."""
    if p.birth_time is not None:
        p.moon_sign = None
        return
    try:
        cands = moonsign.candidate_signs(p.birth_date, p.timezone, p.utc_offset_minutes)
    except (ValueError, OverflowError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if len(cands) == 1:
        p.moon_sign = cands[0]
    elif chosen in cands:
        p.moon_sign = chosen
    elif chosen is None and p.moon_sign in cands:
        pass  # an edit that did not change the answer: keep the earlier choice
    else:
        raise HTTPException(status_code=422, detail={
            "message": "The birth time is unknown and the Moon changed sign that day: choose one of the two signs.",
            "candidates": cands})


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
    settle_moon_sign(profile, body.moon_sign)
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
    if "birth_time" in sent:
        profile.birth_time = body.birth_time  # null = the time is not known
    if sent & {"place_id", "lat", "lon", "tz"}:
        _apply_location(profile, resolve_location(db, body.place_id, body.lat, body.lon, body.tz))
    if "utc_offset_minutes" in sent:
        profile.utc_offset_minutes = body.utc_offset_minutes
    settle_moon_sign(profile, body.moon_sign)  # the date, time or place may have changed the answer
    if sent & {"birth_date", "birth_time", "place_id", "lat", "lon", "tz", "utc_offset_minutes"}:
        daily_text.forget(db, profile)  # the written horoscopes were made from the old details
        love_reading.forget(db, profile)
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
    if p.birth_time is None:
        raise HTTPException(status_code=409, detail="The birth time is not known, so a full chart (lagna, houses, "
                                                    "dasha) cannot be calculated. Add the birth time first.")
    if as_of is not None:
        check_date("as_of", as_of)
    place = db.get(Place, p.place_id) if p.place_id else None
    location = Location(p.latitude, p.longitude, p.timezone, place)
    return build_kundli(birth_date=p.birth_date, birth_time=p.birth_time, location=location,
                        utc_offset_minutes=p.utc_offset_minutes, node=node, as_of_date=as_of)


export_router = APIRouter(prefix="/v1/me", tags=["me"],
                          dependencies=[Depends(limit("me", "rate_limit_default_per_minute"))])


class FeedbackExport(BaseModel):
    subject: str
    date: date_type
    rating: int
    felt_accurate: bool | None
    created_at: datetime


class DeviceExport(BaseModel):
    platform: str
    created_at: datetime
    last_seen_at: datetime
    active: bool


class NotificationExport(BaseModel):
    daily_enabled: bool
    daily_time: str
    devices: list[DeviceExport]


class ChatMessageExport(BaseModel):
    role: str
    text: str
    created_at: datetime


class ChatExport(BaseModel):
    id: str
    title: str | None
    created_at: datetime
    messages: list[ChatMessageExport]


class DailyHoroscopeExport(BaseModel):
    date: date_type
    lang: str
    text: str
    created_at: datetime


class LoveReadingExport(BaseModel):
    lang: str
    text: str
    created_at: datetime


class ExportOut(BaseModel):
    account: UserOut
    consented_at: datetime | None
    profiles: list[ProfileOut]
    horoscope_feedback: list[FeedbackExport] = []
    notifications: NotificationExport | None = None
    chats: list[ChatExport] = []
    daily_horoscopes: list[DailyHoroscopeExport] = []
    love_readings: list[LoveReadingExport] = []


@export_router.get("/export", response_model=ExportOut)
def export_my_data(user: User = Depends(get_current_user)) -> ExportOut:
    """Everything we hold about the signed-in user, in one response."""
    return ExportOut(account=UserOut.from_user(user), consented_at=user.consented_at,
                     profiles=[ProfileOut.from_profile(p) for p in user.profiles],
                     horoscope_feedback=[FeedbackExport(subject=f.subject, date=f.local_date, rating=f.rating,
                                                        felt_accurate=f.felt_accurate, created_at=f.created_at)
                                         for f in user.feedback],
                     notifications=_notifications_export(user),
                     chats=[ChatExport(id=str(c.id), title=c.title, created_at=c.created_at,
                                       messages=[ChatMessageExport(role=m.role, text=m.text, created_at=m.created_at)
                                                 for m in c.messages]) for c in user.conversations],
                     daily_horoscopes=[DailyHoroscopeExport(date=h.local_date, lang=h.lang, text=h.text,
                                                            created_at=h.created_at) for h in user.daily_horoscopes],
                     love_readings=[LoveReadingExport(lang=r.lang, text=r.text, created_at=r.created_at)
                                    for r in user.love_readings])


def _notifications_export(user: User) -> NotificationExport | None:
    p = user.notification_prefs
    if p is None and not user.devices:
        return None
    # Push tokens are credentials for a phone, so the export lists devices without the token itself.
    return NotificationExport(
        daily_enabled=bool(p and p.daily_enabled),
        daily_time=p.daily_time.strftime("%H:%M") if p else "07:30",
        devices=[DeviceExport(platform=d.platform, created_at=d.created_at, last_seen_at=d.last_seen_at,
                              active=d.disabled_at is None) for d in user.devices])
