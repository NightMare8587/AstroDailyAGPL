"""The written daily horoscope for the signed-in user's own profile. Personal data: consent required."""
from datetime import date as date_type, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..chat.context import day_location
from ..chat.llm import GeminiClient, LlmClient, LlmError
from ..config import get_settings
from ..db import get_db
from ..horoscope import daily_text, service
from ..horoscope.card import DISCLAIMER
from ..models import User, primary_profile
from ..ratelimit import limit
from .profile_routes import require_consent

Lang = Literal["en", "hi"]

router = APIRouter(prefix="/v1/me/horoscope", tags=["horoscope"],
                   dependencies=[Depends(limit("chat", "rate_limit_chat_per_minute"))])


def get_daily_llm_client() -> LlmClient | None:
    """None when no API key is configured (the endpoint then answers 503). Tests override this."""
    s = get_settings()
    if not s.gemini_api_key:
        return None
    return GeminiClient(s.gemini_api_key, s.gemini_model, s.daily_horoscope_max_output_tokens, s.chat_timeout_seconds)


class DailyTextOut(BaseModel):
    date: date_type
    lang: Lang
    text: str
    status: str  # "draft" until the wording is reviewed
    disclaimer: dict[str, str]


@router.get("/text", response_model=DailyTextOut)
def daily_horoscope_text(date: date_type | None = None, lang: Lang = "en", user: User = Depends(require_consent),
                         db: Session = Depends(get_db), client: LlmClient | None = Depends(get_daily_llm_client)
                         ) -> DailyTextOut:
    profile = primary_profile(user)
    if profile is None:
        raise HTTPException(status_code=404, detail="No birth profile yet. Create one with POST /v1/profiles.")
    today = service.today_in(day_location(user, profile).timezone)
    day = date or today
    if not today <= day <= today + timedelta(days=1):
        raise HTTPException(status_code=422, detail="The written horoscope is available for today and tomorrow.")
    try:
        row = daily_text.get_or_build(db, user, profile, day, lang, client)
    except daily_text.FreeLimitReached:
        raise HTTPException(status_code=402, detail="You have used your free written horoscopes.")
    except LlmError:
        raise HTTPException(status_code=503, detail="The horoscope is unavailable right now. Please try again shortly.")
    return DailyTextOut(date=row.local_date, lang=row.lang, text=row.text, status=row.status,
                        disclaimer=dict(DISCLAIMER))
