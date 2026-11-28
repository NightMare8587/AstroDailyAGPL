"""The written summary of a compatibility match. Built by the model from the match's numbers (no names, no birth
details) the first time it is asked for, then saved for that ordered pair and language."""
import logging

from sqlalchemy import delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..calc import matching, names, zodiac
from ..chat.llm import LlmClient, LlmError, Turn
from ..chat.prompt import MATCH_REQUEST, RETRY_NOTE, match_system_prompt
from ..chat.safety import breaks_tone_rules
from ..models import BirthProfile, MatchSummary, User

log = logging.getLogger("astrodaily.horoscope")


def saved(db: Session, first: BirthProfile, second: BirthProfile, lang: str) -> MatchSummary | None:
    return db.scalar(select(MatchSummary).where(
        MatchSummary.first_profile_id == first.id, MatchSummary.second_profile_id == second.id, MatchSummary.lang == lang))


def forget(db: Session, profile: BirthProfile) -> None:
    """A profile's birth details changed, so every summary that used it no longer fits."""
    db.execute(delete(MatchSummary).where(or_(MatchSummary.first_profile_id == profile.id,
                                              MatchSummary.second_profile_id == profile.id)))


def context(result: dict, a: matching.Moon, b: matching.Moon, you_first: bool) -> str:
    """The match as plain lines. [you_first] says whether the first column is you or the other person."""
    who = ("you", "the other person") if you_first else ("the other person", "you")

    def person(label: str, m: matching.Moon) -> str:
        return f"{label}: Moon in {zodiac.SIGNS[m.sign - 1][0]}, birth star {names.NAKSHATRA[m.nakshatra - 1][0]}."

    lines = [person(f"First column ({who[0]})", a), person(f"Second column ({who[1]})", b),
             f"Total: {result['total']:g} out of {result['max']}."]
    for p in result["parts"]:
        lines.append(f"{p['key'].replace('_', ' ').title()}: {p['points']:g} of {p['max']}.")
    return "\n".join(lines)


def get_or_build(db: Session, user: User, first: BirthProfile, second: BirthProfile, you_first: bool, lang: str,
                 a: matching.Moon, b: matching.Moon, result: dict, client: LlmClient | None) -> MatchSummary:
    found = saved(db, first, second, lang)
    if found is not None:
        return found
    if client is None:
        raise LlmError("not configured")
    system = match_system_prompt(lang, context(result, a, b, you_first))
    turns = [Turn("user", MATCH_REQUEST)]
    out = client.generate(system, turns)
    if breaks_tone_rules(out.text):
        log.info("match summary broke tone rules; retrying once")
        out = client.generate(system + RETRY_NOTE, turns)
    if breaks_tone_rules(out.text):
        raise LlmError("tone")
    row = MatchSummary(user_id=user.id, first_profile_id=first.id, second_profile_id=second.id, lang=lang,
                       text=out.text.strip(), status="draft", model=out.model, tokens_in=out.tokens_in,
                       tokens_out=out.tokens_out)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:  # two opens at once: the first one wins and both get the same text
        db.rollback()
        winner = saved(db, first, second, lang)
        if winner is None:
            raise
        return winner
    return row
