"""The written love and partnership reading. Built by the model from the engine's chart facts the first time a person
asks, then saved. It comes from the birth chart alone, so it is the same on every day."""
import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..calc import zodiac
from ..calc.kundli import compute_chart, resolve_birth_moment
from ..chat.llm import LlmClient, LlmError, Turn
from ..chat.prompt import LOVE_REQUEST, RETRY_NOTE, love_system_prompt
from ..chat.safety import breaks_tone_rules
from ..models import BirthProfile, LoveReading, User

log = logging.getLogger("astrodaily.horoscope")

KARAKAS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")


class NeedsBirthTime(Exception):
    """The reading uses the Lagna and the Navamsa, which need the birth time."""


def saved(db: Session, profile: BirthProfile, lang: str) -> LoveReading | None:
    return db.scalar(select(LoveReading).where(LoveReading.profile_id == profile.id, LoveReading.lang == lang))


def forget(db: Session, profile: BirthProfile) -> None:
    """The birth details changed, so what was written from the old ones no longer fits."""
    for r in list(profile.love_readings):
        db.delete(r)


def _sign(n: int) -> str:
    return zodiac.SIGNS[n - 1][0]


def key_facts(chart: dict) -> dict:
    """The chart facts the reading and the page both use, as plain data (sign numbers 1..12, planet keys)."""
    lagna = chart["lagna"]["sign"]
    planets = {p["key"]: p for p in chart["planets"]}
    seventh = (lagna + 5) % 12 + 1
    lord = zodiac.SIGN_LORDS[seventh - 1]
    # The planet with the fewest degrees in its sign is the Darakaraka (partner significator) in the common seven-karaka scheme.
    dara = min((planets[k] for k in KARAKAS), key=lambda p: p["degree_in_sign"])
    nav_lagna = chart["lagna"]["navamsa_sign"]
    nav_seventh = (nav_lagna + 5) % 12 + 1
    return {
        "lagna": lagna,
        "seventh_sign": seventh,
        "seventh_lord": {"key": lord, "sign": planets[lord]["sign"], "house": planets[lord]["house"],
                         "dignity": planets[lord]["dignity"]},
        "in_seventh": [k for k, p in planets.items() if p["house"] == 7],
        "venus": {"sign": planets["Venus"]["sign"], "house": planets["Venus"]["house"],
                  "dignity": planets["Venus"]["dignity"], "retrograde": planets["Venus"]["retrograde"]},
        "darakaraka": {"key": dara["key"], "sign": dara["sign"], "house": dara["house"], "dignity": dara["dignity"]},
        "navamsa_lagna": nav_lagna,
        "navamsa_seventh": nav_seventh,
        "navamsa_seventh_lord": zodiac.SIGN_LORDS[nav_seventh - 1],
        "navamsa_venus": planets["Venus"]["navamsa_sign"],
    }


def facts(chart: dict) -> str:
    """The chart facts the reading may use, as plain lines. Derived facts only."""
    f = key_facts(chart)

    def placed(sign: int, house: int, dignity: str | None) -> str:
        return f"{_sign(sign)} (house {house}{', ' + dignity if dignity else ''})"

    lord, venus, dara = f["seventh_lord"], f["venus"], f["darakaraka"]
    return "\n".join([
        f"Ascendant (lagna): {_sign(f['lagna'])}.",
        f"7th house of partnership: {_sign(f['seventh_sign'])}, ruled by {lord['key']}. {lord['key']} is in "
        f"{placed(lord['sign'], lord['house'], lord['dignity'])}.",
        "Planets in the 7th house: " + (", ".join(f["in_seventh"]) or "none") + ".",
        f"Venus (love, attraction): in {placed(venus['sign'], venus['house'], venus['dignity'])}"
        + (", retrograde" if venus["retrograde"] else "") + ".",
        f"Planet that shows the partner (Darakaraka, the planet with the fewest degrees in its sign): {dara['key']}, "
        f"in {placed(dara['sign'], dara['house'], dara['dignity'])}.",
        f"Navamsa (D9, the chart of marriage and inner strength): lagna {_sign(f['navamsa_lagna'])}; its 7th house is "
        f"{_sign(f['navamsa_seventh'])}, ruled by {f['navamsa_seventh_lord']}; Venus is in {_sign(f['navamsa_venus'])}.",
    ])


def chart_for(profile: BirthProfile) -> dict:
    if profile.birth_time is None:
        raise NeedsBirthTime
    birth = resolve_birth_moment(profile.birth_date, profile.birth_time, profile.timezone, profile.utc_offset_minutes)
    return compute_chart(birth, profile.latitude, profile.longitude, "mean")


def get_or_build(db: Session, user: User, profile: BirthProfile, lang: str, client: LlmClient | None) -> LoveReading:
    """The saved reading, or a new one. Raises NeedsBirthTime, or LlmError when the model is unavailable (nothing is
    saved then, so the next open simply tries again)."""
    found = saved(db, profile, lang)
    if found is not None:
        return found
    chart = chart_for(profile)
    if client is None:
        raise LlmError("not configured")
    system = love_system_prompt(lang, facts(chart))
    turns = [Turn("user", LOVE_REQUEST)]
    result = client.generate(system, turns)
    if breaks_tone_rules(result.text):
        log.info("love reading broke tone rules; retrying once")
        result = client.generate(system + RETRY_NOTE, turns)
    if breaks_tone_rules(result.text):
        raise LlmError("tone")
    row = LoveReading(user_id=user.id, profile_id=profile.id, lang=lang, text=result.text.strip(), status="draft",
                      model=result.model, tokens_in=result.tokens_in, tokens_out=result.tokens_out)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:  # two opens at once: the first one wins and both get the same text
        db.rollback()
        winner = saved(db, profile, lang)
        if winner is None:
            raise
        return winner
    return row
