"""The written love and partnership reading for the signed-in user's own profile. Personal data: consent required."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..calc import zodiac
from ..calc.kundli import names_pair
from ..chat.llm import LlmClient, LlmError
from ..db import get_db
from ..horoscope import love_reading
from ..horoscope.card import DISCLAIMER
from ..models import User, primary_profile
from ..ratelimit import limit
from .daily_text_routes import get_daily_llm_client
from .profile_routes import require_consent

Lang = Literal["en", "hi"]

router = APIRouter(prefix="/v1/me/reading", tags=["reading"],
                   dependencies=[Depends(limit("chat", "rate_limit_chat_per_minute"))])


class Named(BaseModel):
    en: str
    hi: str


class SignRef(Named):
    number: int


class PlanetRef(BaseModel):
    key: str
    name: Named


class PlacedPlanet(PlanetRef):
    sign: SignRef
    house: int
    dignity: str | None = None


class LoveFacts(BaseModel):
    """The chart facts behind the reading, for the page to show as icons."""
    lagna: SignRef
    seventh_sign: SignRef
    seventh_lord: PlacedPlanet
    in_seventh: list[PlanetRef]
    venus: PlacedPlanet
    navamsa_lagna: SignRef
    navamsa_seventh: SignRef


class LoveReadingOut(BaseModel):
    lang: Lang
    text: str
    status: str  # "draft" until the wording is reviewed
    facts: LoveFacts
    disclaimer: dict[str, str]


def _sign(n: int) -> SignRef:
    return SignRef(number=n, **names_pair(zodiac.SIGNS[n - 1]))


def _planet(key: str) -> PlanetRef:
    return PlanetRef(key=key, name=Named(**names_pair(zodiac.PLANET_NAMES[key])))


def _placed(key: str, sign: int, house: int, dignity: str | None) -> PlacedPlanet:
    return PlacedPlanet(key=key, name=Named(**names_pair(zodiac.PLANET_NAMES[key])), sign=_sign(sign), house=house,
                        dignity=dignity)


def _facts(profile) -> LoveFacts:
    f = love_reading.key_facts(love_reading.chart_for(profile))
    lord, venus = f["seventh_lord"], f["venus"]
    return LoveFacts(
        lagna=_sign(f["lagna"]), seventh_sign=_sign(f["seventh_sign"]),
        seventh_lord=_placed(lord["key"], lord["sign"], lord["house"], lord["dignity"]),
        in_seventh=[_planet(k) for k in f["in_seventh"]],
        venus=_placed("Venus", venus["sign"], venus["house"], venus["dignity"]),
        navamsa_lagna=_sign(f["navamsa_lagna"]), navamsa_seventh=_sign(f["navamsa_seventh"]))


@router.get("/love", response_model=LoveReadingOut)
def love(lang: Lang = "en", user: User = Depends(require_consent), db: Session = Depends(get_db),
         client: LlmClient | None = Depends(get_daily_llm_client)) -> LoveReadingOut:
    profile = primary_profile(user)
    if profile is None:
        raise HTTPException(status_code=404, detail="No birth profile yet. Create one with POST /v1/profiles.")
    try:
        row = love_reading.get_or_build(db, user, profile, lang, client)
    except love_reading.NeedsBirthTime:
        raise HTTPException(status_code=409, detail="The love reading needs your birth time.")
    except LlmError:
        raise HTTPException(status_code=503, detail="The reading is unavailable right now. Please try again shortly.")
    return LoveReadingOut(lang=row.lang, text=row.text, status=row.status, facts=_facts(profile),
                          disclaimer=dict(DISCLAIMER))
