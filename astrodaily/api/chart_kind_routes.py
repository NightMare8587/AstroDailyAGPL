"""A saved profile's other charts, each with a reading for every planet in it: the Moon chart (the same signs counted
from the Moon sign), the Navamsa (D9), the Saptamsa (D7) and the Dashamsa (D10). The planet-in-sign and planet-in-house
text is the same content library the birth chart uses. Personal data: consent required."""
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..calc import zodiac
from ..calc.kundli import names_pair
from ..content import chart_meanings
from ..db import get_db
from ..horoscope import love_reading
from ..models import User
from ..ratelimit import limit
from .kundli_routes import MeaningOut, Named, PlanetOut, SignOut, _meaning, _sign  # noqa: F401
from .profile_routes import _own_profile, require_consent

Kind = Literal["moon", "navamsa", "saptamsa", "dashamsa"]

router = APIRouter(prefix="/v1/profiles", tags=["profiles"],
                   dependencies=[Depends(limit("kundli", "rate_limit_panchang_per_minute"))])

_SIGN_FIELD = {"navamsa": "navamsa_sign", "saptamsa": "saptamsa_sign", "dashamsa": "dashamsa_sign"}


class ChartPlanetOut(BaseModel):
    key: str
    name: Named
    sign: SignOut
    house: int
    retrograde: bool
    meaning: MeaningOut | None = None


class ChartKindOut(BaseModel):
    kind: Kind
    lagna: SignOut  # the first house's sign in this chart (for the Moon chart, the Moon's sign)
    lagna_meaning: MeaningOut | None = None  # not for the Moon chart
    planets: list[ChartPlanetOut]


def build_chart(chart: dict, kind: str) -> ChartKindOut:
    """The chosen chart worked out from the birth chart's numbers."""
    planets = chart["planets"]
    if kind == "moon":
        lagna = next(p["sign"] for p in planets if p["key"] == "Moon")
        sign_of = lambda p: p["sign"]  # noqa: E731  the birth signs, counted from the Moon
    else:
        lagna = chart["lagna"][_SIGN_FIELD[kind]]
        sign_of = lambda p: p[_SIGN_FIELD[kind]]  # noqa: E731
    out = []
    for p in planets:
        sign = sign_of(p)
        house = (sign - lagna) % 12 + 1
        out.append(ChartPlanetOut(
            key=p["key"], name=Named(**p["name"]), sign=_sign(sign), house=house, retrograde=p["retrograde"],
            meaning=_meaning(chart_meanings.planet_meaning(p["key"], sign, names_pair(zodiac.SIGNS[sign - 1]), house))))
    lagna_meaning = None if kind == "moon" else _meaning(chart_meanings.lagna_meaning(lagna))
    return ChartKindOut(kind=kind, lagna=_sign(lagna), lagna_meaning=lagna_meaning, planets=out)


@router.get("/{profile_id}/chart/{kind}", response_model=ChartKindOut)
def profile_chart(profile_id: uuid.UUID, kind: Kind, user: User = Depends(require_consent),
                  db: Session = Depends(get_db)) -> ChartKindOut:
    p = _own_profile(db, user, profile_id)
    try:
        chart = love_reading.chart_for(p)
    except love_reading.NeedsBirthTime:
        raise HTTPException(status_code=409, detail="The birth time is not known, so these charts cannot be calculated.")
    return build_chart(chart, kind)
