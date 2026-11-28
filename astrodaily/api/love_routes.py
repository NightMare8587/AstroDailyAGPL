"""The written love and partnership reading for the signed-in user's own profile. Personal data: consent required."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

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


class LoveReadingOut(BaseModel):
    lang: Lang
    text: str
    status: str  # "draft" until the wording is reviewed
    disclaimer: dict[str, str]


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
    return LoveReadingOut(lang=row.lang, text=row.text, status=row.status, disclaimer=dict(DISCLAIMER))
