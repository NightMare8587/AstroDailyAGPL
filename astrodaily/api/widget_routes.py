"""The home-screen widget's background refresh. The phone keeps a narrow, long-lived widget token (it can read this one
card and nothing else) so a background job never touches the session's rotating refresh token."""
import logging
from datetime import date as date_type, datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth.deps import get_widget_user
from ..auth.tokens import create_widget_token
from ..chat.llm import LlmClient, LlmError
from ..db import get_db
from ..horoscope import daily_text
from ..models import User, primary_profile
from ..ratelimit import limit
from .daily_text_routes import get_daily_llm_client
from .horoscope_routes import Named, WidgetOut, widget_for
from .planet_card_routes import PlanetCardsOut, cards_for
from .profile_routes import require_consent

log = logging.getLogger("astrodaily.widget")
Lang = Literal["en", "hi"]

token_router = APIRouter(prefix="/v1/me", tags=["widget"], dependencies=[Depends(limit("me", "rate_limit_default_per_minute"))])
card_router = APIRouter(prefix="/v1/widget", tags=["widget"], dependencies=[Depends(limit("widget", "rate_limit_default_per_minute"))])


class WidgetTokenOut(BaseModel):
    token: str
    expires_at: datetime


class WidgetCardOut(WidgetOut):
    sign: Named | None = None      # the person's Moon sign
    paragraph: str | None = None   # today's written horoscope, when it could be made


@token_router.post("/widget-token", response_model=WidgetTokenOut)
def issue_widget_token(user: User = Depends(require_consent)) -> WidgetTokenOut:
    """A token for the home-screen widget's background refresh. Ask again whenever the app is opened; each sign-out
    revokes the ones issued before it."""
    token, exp = create_widget_token(user.id)
    return WidgetTokenOut(token=token, expires_at=exp)


@card_router.get("/card", response_model=WidgetCardOut)
def widget_card(lang: Lang = "en", user: User = Depends(get_widget_user), db: Session = Depends(get_db),
                client: LlmClient | None = Depends(get_daily_llm_client)) -> WidgetCardOut:
    """Today's card for the widget: score, the good time, the Moon sign and the written paragraph. Consent is checked
    here too, as for every personal endpoint."""
    from fastapi import HTTPException
    if user.consented_at is None:
        raise HTTPException(status_code=403, detail="Consent is required")
    out, card = widget_for(user, db, None, lang)
    paragraph = None
    profile = primary_profile(user)
    if profile is not None:
        try:
            paragraph = daily_text.get_or_build(db, user, profile, card.date, lang, client).text
        except (LlmError, daily_text.FreeLimitReached):
            pass  # the widget falls back to the first suggestion
        except Exception:  # the widget must still get its score and times
            log.exception("widget paragraph failed")
    sign = card.subject.rashi_name
    return WidgetCardOut(**out.model_dump(), sign=Named(en=sign.en, hi=sign.hi) if sign else None, paragraph=paragraph)


@card_router.get("/planets", response_model=PlanetCardsOut)
def widget_planets(lang: Lang = "en", user: User = Depends(get_widget_user), db: Session = Depends(get_db),
                   client: LlmClient | None = Depends(get_daily_llm_client)) -> PlanetCardsOut:
    """Today's five planet cards for the planet widget. Consent is checked here too."""
    from fastapi import HTTPException
    if user.consented_at is None:
        raise HTTPException(status_code=403, detail="Consent is required")
    return cards_for(user, db, client, None, lang)
