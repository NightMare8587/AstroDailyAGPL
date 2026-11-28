"""Compatibility (Ashtakoota, 36 points) between the signed-in user's own profile and another saved profile.
Personal data: consent required. Nothing is stored: the match is worked out from the two Moon positions each time."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..calc import matching, names, zodiac
from ..calc.kundli import names_pair
from ..content import match_text
from ..db import get_db
from ..horoscope import love_reading
from ..horoscope.card import DISCLAIMER
from ..models import BirthProfile, User, primary_profile
from ..ratelimit import limit
from .profile_routes import _own_profile, require_consent

router = APIRouter(prefix="/v1/me/match", tags=["match"],
                   dependencies=[Depends(limit("match", "rate_limit_default_per_minute"))])


class Named(BaseModel):
    en: str
    hi: str


class NumberedName(Named):
    number: int


class PersonOut(BaseModel):
    label: str
    moon_sign: NumberedName
    nakshatra: NumberedName


class PartOut(BaseModel):
    key: str
    name: Named
    about: Named
    points: float
    max: int
    a: Named  # what it is for the signed-in person
    b: Named  # what it is for the other person


class MatchOut(BaseModel):
    a: PersonOut  # the signed-in person (the first column of the tables)
    b: PersonOut
    total: float
    max: int
    band: str  # great | good | fair | low
    band_text: Named
    parts: list[PartOut]
    disclaimer: dict[str, str]


def _named(pair: tuple[str, str]) -> Named:
    return Named(**names_pair(pair))


def _moon(profile: BirthProfile) -> matching.Moon:
    chart = love_reading.chart_for(profile)  # raises NeedsBirthTime
    return matching.Moon(next(p["longitude"] for p in chart["planets"] if p["key"] == "Moon"))


def _person(profile: BirthProfile, moon: matching.Moon) -> PersonOut:
    return PersonOut(label=profile.label,
                     moon_sign=NumberedName(number=moon.sign, **names_pair(zodiac.SIGNS[moon.sign - 1])),
                     nakshatra=NumberedName(number=moon.nakshatra, **names_pair(names.NAKSHATRA[moon.nakshatra - 1])))


def _value(key: str, v: object) -> Named:
    """The names of what each person has for one part: a group, an animal, a planet, a sign or a birth star."""
    if key == "tara":
        return _named(names.NAKSHATRA[int(v) - 1])
    if key == "bhakoot":
        return _named(zodiac.SIGNS[int(v) - 1])
    if key == "graha_maitri":
        return _named(zodiac.PLANET_NAMES[str(v)])
    return _named(match_text.VALUES[str(v)])


@router.get("/{profile_id}", response_model=MatchOut)
def match_with(profile_id: uuid.UUID, user: User = Depends(require_consent), db: Session = Depends(get_db)) -> MatchOut:
    me = primary_profile(user)
    if me is None:
        raise HTTPException(status_code=404, detail="No birth profile yet. Create one with POST /v1/profiles.")
    other = _own_profile(db, user, profile_id)
    if other.id == me.id:
        raise HTTPException(status_code=422, detail="Choose someone other than yourself.")
    for p in (me, other):
        if p.birth_time is None:
            raise HTTPException(status_code=409, detail="The match needs the birth time of both people.")
    ma, mb = _moon(me), _moon(other)
    result = matching.match(ma, mb)
    key, en, hi = match_text.band(result["total"])
    return MatchOut(
        a=_person(me, ma), b=_person(other, mb), total=result["total"], max=result["max"], band=key,
        band_text=Named(en=en, hi=hi),
        parts=[PartOut(key=p["key"], name=_named(match_text.PARTS[p["key"]][0]), about=_named(match_text.PARTS[p["key"]][1]),
                       points=p["points"], max=p["max"], a=_value(p["key"], p["a"]), b=_value(p["key"], p["b"]))
               for p in result["parts"]],
        disclaimer=dict(DISCLAIMER))
