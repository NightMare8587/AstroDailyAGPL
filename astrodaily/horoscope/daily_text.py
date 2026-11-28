"""The written daily horoscope. Built by the model from the engine's facts the first time a person asks for a day,
then saved, so it does not change that day and costs nothing on later opens."""
import logging
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..chat.context import build_context
from ..chat.llm import LlmClient, LlmError, Turn
from ..chat.prompt import DAILY_REQUEST, RETRY_NOTE, daily_system_prompt
from ..chat.safety import breaks_tone_rules
from ..billing.service import is_premium
from ..config import get_settings
from ..models import BirthProfile, DailyHoroscope, User

log = logging.getLogger("astrodaily.horoscope")


class FreeLimitReached(Exception):
    """The account has used its free written horoscopes (only possible when a limit is configured)."""


def saved(db: Session, profile: BirthProfile, day: date, lang: str) -> DailyHoroscope | None:
    return db.scalar(select(DailyHoroscope).where(
        DailyHoroscope.profile_id == profile.id, DailyHoroscope.local_date == day, DailyHoroscope.lang == lang))


def days_used(db: Session, user: User) -> int:
    return db.scalar(select(func.count(func.distinct(DailyHoroscope.local_date))).where(
        DailyHoroscope.user_id == user.id)) or 0


def forget(db: Session, profile: BirthProfile) -> None:
    """The birth details changed, so what was written from the old ones no longer fits."""
    for h in list(profile.daily_horoscopes):
        db.delete(h)


def get_or_build(db: Session, user: User, profile: BirthProfile, day: date, lang: str,
                 client: LlmClient | None) -> DailyHoroscope:
    """The saved horoscope, or a new one. Raises FreeLimitReached, or LlmError when the model is unavailable
    (nothing is saved then, so the next open simply tries again)."""
    s = get_settings()
    # The written paragraph is a paying feature (and costs a model call): nothing for a free account, saved or not.
    if s.daily_horoscope_requires_premium and not is_premium(user):
        raise FreeLimitReached
    found = saved(db, profile, day, lang)
    if found is not None:
        return found
    # Another language for a day already written does not use up a free day.
    if s.daily_horoscope_free_limit > 0:
        has_day = db.scalar(select(func.count(DailyHoroscope.id)).where(
            DailyHoroscope.user_id == user.id, DailyHoroscope.local_date == day))
        if not has_day and days_used(db, user) >= s.daily_horoscope_free_limit:
            raise FreeLimitReached
    if client is None:
        raise LlmError("not configured")
    system = daily_system_prompt(lang, build_context(user, profile, day))
    turns = [Turn("user", DAILY_REQUEST)]
    result = client.generate(system, turns)
    if breaks_tone_rules(result.text):
        log.info("daily horoscope broke tone rules; retrying once")
        result = client.generate(system + RETRY_NOTE, turns)
    if breaks_tone_rules(result.text):
        raise LlmError("tone")  # a fixed stand-in would be saved for the whole day, so save nothing
    row = DailyHoroscope(user_id=user.id, profile_id=profile.id, local_date=day, lang=lang, text=result.text.strip(),
                         status="draft", model=result.model, tokens_in=result.tokens_in, tokens_out=result.tokens_out)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:  # two opens at once: the first one wins and both get the same text
        db.rollback()
        winner = saved(db, profile, day, lang)
        if winner is None:
            raise
        return winner
    return row
