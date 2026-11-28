"""The daily planet cards for the signed-in user's own profile. Personal data: consent required."""
from datetime import date as date_type, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..chat.context import day_location
from ..chat.llm import LlmClient, LlmError
from ..db import get_db
from ..horoscope import love_reading, planet_cards, service
from ..horoscope.card import DISCLAIMER
from ..models import User, primary_profile
from ..ratelimit import limit
from .daily_text_routes import get_daily_llm_client
from .profile_routes import require_consent

Lang = Literal["en", "hi"]

router = APIRouter(prefix="/v1/me/horoscope", tags=["horoscope"],
                   dependencies=[Depends(limit("chat", "rate_limit_chat_per_minute"))])


class Named(BaseModel):
    en: str
    hi: str


class SignOut(Named):
    number: int


class MeaningLines(BaseModel):
    in_sign: Named
    in_house: Named | None = None


class PlanetCardOut(BaseModel):
    area: str  # career | money | relationships | health | mind
    area_name: Named
    planet: str
    planet_name: Named
    sign: SignOut
    house: int
    dignity: str | None
    retrograde: bool
    score: int  # the day's score for the area, out of 5
    headline: str
    message: str
    meaning: MeaningLines | None  # the planet in its sign and house, from the content library
    status: str  # "draft" until the wording is reviewed


class PlanetCardsOut(BaseModel):
    date: date_type
    lang: Lang
    cards: list[PlanetCardOut]
    disclaimer: dict[str, str]


def cards_for(user: User, db: Session, client: LlmClient | None, date: date_type | None, lang: str) -> PlanetCardsOut:
    """The day's cards for the user's own profile. Shared by the app and the widget."""
    profile = primary_profile(user)
    if profile is None:
        raise HTTPException(status_code=404, detail="No birth profile yet. Create one with POST /v1/profiles.")
    today = service.today_in(day_location(user, profile).timezone)
    day = date or today
    if not today <= day <= today + timedelta(days=1):
        raise HTTPException(status_code=422, detail="The planet cards are available for today and tomorrow.")
    try:
        cards = planet_cards.get_or_build(db, user, profile, day, lang, client)
    except love_reading.NeedsBirthTime:
        raise HTTPException(status_code=409, detail="The planet cards need your birth time.")
    except LlmError:
        raise HTTPException(status_code=503, detail="The cards are unavailable right now. Please try again shortly.")
    return PlanetCardsOut(date=day, lang=lang, cards=[PlanetCardOut(**c) for c in cards], disclaimer=dict(DISCLAIMER))


@router.get("/planets", response_model=PlanetCardsOut)
def planet_cards_for_day(date: date_type | None = None, lang: Lang = "en", user: User = Depends(require_consent),
                         db: Session = Depends(get_db), client: LlmClient | None = Depends(get_daily_llm_client)
                         ) -> PlanetCardsOut:
    return cards_for(user, db, client, date, lang)
