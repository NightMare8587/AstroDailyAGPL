"""Daily horoscope cards: by Moon sign (public), per saved profile, and the signed-in user's own."""
import uuid
from datetime import date as date_type
from datetime import datetime
from typing import Any, Literal

import swisseph as swe
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth.deps import get_current_user, get_optional_user
from ..calc import zodiac
from ..content import catalog as content_catalog
from ..content.apply import localize
from ..db import get_db, get_optional_db
from ..horoscope import service
from ..horoscope.card import DISCLAIMER
from ..horoscope.report import ENGINE_VERSION
from ..horoscope.rules import RULESET_VERSION
from ..models import BirthProfile, HoroscopeFeedback, User
from ..ratelimit import limit
from .birth import check_date, place_label, resolve_location
from .profile_routes import _own_profile, require_consent

Lang = Literal["en", "hi"]


class Named(BaseModel):
    en: str
    hi: str


class LocationOut(BaseModel):
    latitude: float
    longitude: float
    timezone: str
    place_name: str | None
    source: str  # explicit_place, coordinates, home, profile or default


class AreaOut(BaseModel):
    key: str
    name: Named
    score: int


class SignalOut(BaseModel):
    id: str
    kind: str
    scope: str
    reason: str                 # the engine's own English wording, always present
    params: dict[str, Any]
    text: str | None = None     # reviewed library wording, when there is some
    text_lang: Lang | None = None


class WindowOut(BaseModel):
    label: str
    start: datetime
    end: datetime
    reason: str


class WindowsOut(BaseModel):
    best: list[WindowOut]
    avoid: list[WindowOut]


class ElementOut(Named):
    number: int
    ends_at: datetime
    paksha: str | None = None


class PanchangBriefOut(BaseModel):
    sunrise: datetime
    sunset: datetime
    vara: Named
    tithi: ElementOut
    nakshatra: ElementOut
    yoga: ElementOut
    karana: ElementOut


class SubjectOut(BaseModel):
    type: Literal["rashi", "profile"]
    rashi: int | None = None
    rashi_name: Named | None = None
    profile_id: uuid.UUID | None = None


class HoroscopeOut(BaseModel):
    date: date_type
    subject: SubjectOut
    level: Literal["A", "B"]
    location: LocationOut
    score: int
    areas: list[AreaOut]
    dos: list[SignalOut]
    donts: list[SignalOut]
    theme: SignalOut | None
    coming_up: SignalOut | None
    windows: WindowsOut
    why: list[SignalOut]
    panchang: PanchangBriefOut
    requested_language: Lang
    text_language: Lang      # the language of the wording (en when the library has none in the requested one)
    translated: bool
    disclaimer: Named
    generated_by: str
    engine_version: str
    ruleset_version: str
    scoring_version: str


class WidgetOut(BaseModel):
    """A few hundred bytes for a home-screen widget or a notification."""
    date: date_type
    score: int
    level: Literal["A", "B"]
    headline: str | None          # the first suggestion, in the card's wording
    caution: str | None
    best_window: WindowOut | None
    avoid_window: WindowOut | None
    timezone: str
    text_language: Lang


def _explicit_location(db: Session | None, place_id: int | None, lat: float | None, lon: float | None,
                       tz: str | None) -> service.DayLocation | None:
    if place_id is None and lat is None and lon is None:
        return None
    loc = resolve_location(db, place_id, lat, lon, tz, what="the location")
    return service.DayLocation(loc.latitude, loc.longitude, loc.timezone,
                               place_label(loc.place), "explicit_place" if loc.place else "coordinates")


def _home_location(user: User | None) -> service.DayLocation | None:
    p = user.home_place if user is not None else None
    if p is None:
        return None
    return service.DayLocation(p.latitude, p.longitude, p.timezone, place_label(p), "home")


def _profile_location(p: BirthProfile) -> service.DayLocation:
    return service.DayLocation(p.latitude, p.longitude, p.timezone, p.place_name, "profile")


def _day(requested: date_type | None, loc: service.DayLocation) -> date_type:
    day = requested or service.today_in(loc.timezone)
    check_date("date", day)
    return day


def _response(core: dict[str, Any], loc: service.DayLocation, subject: SubjectOut, lang: Lang,
              db: Session | None, seed: str) -> HoroscopeOut:
    card, in_lang = localize(service.with_location(core, loc), content_catalog.get_catalog(db), lang,
                             f"{seed}:{core['date']}")
    return HoroscopeOut(
        **card, subject=subject, requested_language=lang, text_language=lang if in_lang else "en",
        translated=in_lang, disclaimer=Named(**DISCLAIMER_NAMED),
    )


DISCLAIMER_NAMED = {"en": DISCLAIMER["en"], "hi": DISCLAIMER["hi"]}


def _compute(call, *args) -> dict[str, Any]:
    try:
        return call(*args)
    except (ValueError, OverflowError, swe.Error) as exc:
        raise HTTPException(status_code=422, detail=str(exc))


def _rashi_subject(rashi: int) -> SubjectOut:
    en, hi = zodiac.SIGNS[rashi - 1]
    return SubjectOut(type="rashi", rashi=rashi, rashi_name=Named(en=en, hi=hi))


# ---------------------------------------------------------------- public: by Moon sign

router = APIRouter(prefix="/v1/horoscope", tags=["horoscope"])


@router.get("/rashi/{rashi}", response_model=HoroscopeOut,
            dependencies=[Depends(limit("horoscope_public", "rate_limit_panchang_per_minute"))])
def rashi_horoscope(
    rashi: int = Path(ge=1, le=12, description="Moon sign, 1 = Aries (Mesha) ... 12 = Pisces (Meena)"),
    date: date_type | None = Query(None, description="Local date; default today at the location"),
    place_id: int | None = Query(None), lat: float | None = Query(None, ge=-66.0, le=66.0),
    lon: float | None = Query(None, ge=-180.0, le=180.0), tz: str | None = Query(None),
    lang: Lang = "en",
    db: Session | None = Depends(get_optional_db),
    user: User | None = Depends(get_optional_user),
) -> HoroscopeOut:
    """Level A card from the Moon sign alone. Location: the one given, else a signed-in user's home city,
    else New Delhi."""
    loc = _explicit_location(db, place_id, lat, lon, tz) or _home_location(user) or service.DEFAULT_LOCATION
    day = _day(date, loc)
    core = _compute(service.rashi_card_core, rashi, day, loc.latitude, loc.longitude, loc.timezone)
    return _response(core, loc, _rashi_subject(rashi), lang, db, f"rashi:{rashi}")


# ---------------------------------------------------------------- personal (consent required)

profile_router = APIRouter(prefix="/v1/profiles", tags=["horoscope"],
                           dependencies=[Depends(limit("horoscope", "rate_limit_default_per_minute"))])
me_router = APIRouter(prefix="/v1/me", tags=["horoscope"],
                      dependencies=[Depends(limit("horoscope", "rate_limit_default_per_minute"))])


def _profile_card(p: BirthProfile, day: date_type, loc: service.DayLocation) -> dict[str, Any]:
    return _compute(service.profile_card_core, p.birth_date, p.birth_time, p.latitude, p.longitude, p.timezone,
                    p.utc_offset_minutes, day, loc.latitude, loc.longitude, loc.timezone)


def _personal(p: BirthProfile, user: User, db: Session, date: date_type | None, place_id: int | None,
              lat: float | None, lon: float | None, tz: str | None, lang: Lang) -> HoroscopeOut:
    # Where is the person today? An explicit place, else their home city, else where they were born.
    loc = _explicit_location(db, place_id, lat, lon, tz) or _home_location(user) or _profile_location(p)
    day = _day(date, loc)
    return _response(_profile_card(p, day, loc), loc, SubjectOut(type="profile", profile_id=p.id), lang, db,
                     f"profile:{p.id}")


@profile_router.get("/{profile_id}/horoscope", response_model=HoroscopeOut)
def profile_horoscope(
    profile_id: uuid.UUID, date: date_type | None = None, place_id: int | None = None,
    lat: float | None = Query(None, ge=-66.0, le=66.0), lon: float | None = Query(None, ge=-180.0, le=180.0),
    tz: str | None = None, lang: Lang = "en",
    user: User = Depends(require_consent), db: Session = Depends(get_db),
) -> HoroscopeOut:
    """Level B card for a saved profile: natal Moon and nakshatra, lagna, running dasha, today's sky."""
    return _personal(_own_profile(db, user, profile_id), user, db, date, place_id, lat, lon, tz, lang)


def _first_profile(user: User) -> BirthProfile:
    if not user.profiles:
        raise HTTPException(status_code=404, detail="No birth profile yet. Create one with POST /v1/profiles.")
    return user.profiles[0]  # the oldest, normally the user's own


@me_router.get("/horoscope", response_model=HoroscopeOut)
def my_horoscope(
    date: date_type | None = None, place_id: int | None = None,
    lat: float | None = Query(None, ge=-66.0, le=66.0), lon: float | None = Query(None, ge=-180.0, le=180.0),
    tz: str | None = None, lang: Lang = "en",
    user: User = Depends(require_consent), db: Session = Depends(get_db),
) -> HoroscopeOut:
    """The signed-in user's own card: their first birth profile."""
    return _personal(_first_profile(user), user, db, date, place_id, lat, lon, tz, lang)


@me_router.get("/horoscope/widget", response_model=WidgetOut)
def my_horoscope_widget(
    date: date_type | None = None, lang: Lang = "en",
    user: User = Depends(require_consent), db: Session = Depends(get_db),
) -> WidgetOut:
    card = _personal(_first_profile(user), user, db, date, None, None, None, None, lang)
    return WidgetOut(
        date=card.date, score=card.score, level=card.level,
        headline=(card.dos[0].text or card.dos[0].reason) if card.dos else None,
        caution=(card.donts[0].text or card.donts[0].reason) if card.donts else None,
        best_window=card.windows.best[0] if card.windows.best else None,
        # The avoid list is in time order; the widget shows Rahu Kaal, the one people know.
        avoid_window=next((w for w in card.windows.avoid if w.label == "Rahu Kaal"),
                          card.windows.avoid[0] if card.windows.avoid else None),
        timezone=card.location.timezone, text_language=card.text_language,
    )


# ---------------------------------------------------------------- feedback

feedback_router = APIRouter(prefix="/v1/horoscope", tags=["horoscope"],
                            dependencies=[Depends(limit("feedback", "rate_limit_default_per_minute"))])


class FeedbackIn(BaseModel):
    subject: str   # "rashi:5" or "profile:<uuid>"
    date: date_type
    rating: Literal[-1, 1]
    felt_accurate: bool | None = None


class FeedbackOut(BaseModel):
    subject: str
    date: date_type
    rating: int
    felt_accurate: bool | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, f: HoroscopeFeedback) -> "FeedbackOut":
        return cls(subject=f.subject, date=f.local_date, rating=f.rating, felt_accurate=f.felt_accurate,
                   created_at=f.created_at, updated_at=f.updated_at)


def _parse_subject(subject: str) -> tuple[str, int | uuid.UUID]:
    kind, _, rest = subject.partition(":")
    try:
        if kind == "rashi" and 1 <= int(rest) <= 12:
            return "rashi", int(rest)
        if kind == "profile":
            return "profile", uuid.UUID(rest)
    except ValueError:
        pass
    raise HTTPException(status_code=422, detail="subject must be 'rashi:1'..'rashi:12' or 'profile:<id>'")


@feedback_router.post("/feedback", response_model=FeedbackOut)
def give_feedback(body: FeedbackIn, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)) -> FeedbackOut:
    """Rate a card. Rating the same card again replaces the earlier rating."""
    check_date("date", body.date)
    kind, ref = _parse_subject(body.subject)
    profile_id = None
    if kind == "profile":
        profile = _own_profile(db, user, ref)  # type: ignore[arg-type]
        profile_id = profile.id
    subject = f"rashi:{ref}" if kind == "rashi" else f"profile:{profile_id}"
    row = db.scalar(select(HoroscopeFeedback).where(
        HoroscopeFeedback.user_id == user.id, HoroscopeFeedback.subject == subject,
        HoroscopeFeedback.local_date == body.date))
    if row is None:
        row = HoroscopeFeedback(user_id=user.id, profile_id=profile_id, subject=subject, local_date=body.date,
                                rating=body.rating, felt_accurate=body.felt_accurate,
                                engine_version=ENGINE_VERSION, ruleset_version=RULESET_VERSION)
        db.add(row)
    else:
        row.rating, row.felt_accurate = body.rating, body.felt_accurate
        row.engine_version, row.ruleset_version = ENGINE_VERSION, RULESET_VERSION
    db.commit()
    return FeedbackOut.from_row(row)
