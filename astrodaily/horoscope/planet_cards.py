"""The daily planet cards: for each life area, one planet from the person's birth chart (Mars for health and energy,
Venus for relationships, ...) with its sign and house, the day's score for the area, and a headline and a one-line
message written by the model. The model's lines are saved for the day; the planet, sign, house and the meaning
sentences come from the chart and the content library each time."""
import json
import logging
import re
from datetime import date

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..calc import zodiac
from ..calc.kundli import names_pair
from ..chat.context import build_context, day_location
from ..chat.llm import LlmClient, LlmError, Turn
from ..chat.prompt import PLANET_CARDS_REQUEST, RETRY_NOTE, planet_cards_system_prompt
from ..chat.safety import breaks_tone_rules
from ..content import chart_meanings
from ..models import BirthProfile, DailyPlanetCards, User
from . import love_reading, service

log = logging.getLogger("astrodaily.horoscope")

# The five areas of the day, in the order the app shows them, each with the planet that stands for it.
AREA_PLANETS = (("career", "Saturn"), ("money", "Jupiter"), ("relationships", "Venus"), ("health", "Mars"),
                ("mind", "Mercury"))
AREAS = tuple(a for a, _ in AREA_PLANETS)


def saved(db: Session, profile: BirthProfile, day: date, lang: str) -> DailyPlanetCards | None:
    return db.scalar(select(DailyPlanetCards).where(
        DailyPlanetCards.profile_id == profile.id, DailyPlanetCards.local_date == day, DailyPlanetCards.lang == lang))


def forget(db: Session, profile: BirthProfile) -> None:
    """The birth details changed, so the cards written from the old ones no longer fit."""
    for r in list(profile.planet_cards):
        db.delete(r)


def _placements(chart: dict) -> dict[str, dict]:
    return {p["key"]: p for p in chart["planets"]}


def _placed(p: dict) -> str:
    extra = (f", {p['dignity']}" if p["dignity"] else "") + (", retrograde" if p["retrograde"] else "")
    return f"{p['key']} in {zodiac.SIGNS[p['sign'] - 1][0]} (house {p['house']}{extra})"


def _context(user: User, profile: BirthProfile, day: date, chart: dict, core: dict) -> str:
    planets = _placements(chart)
    scores = {a["key"]: a["score"] for a in core["areas"]}
    names = {a["key"]: a["name"]["en"] for a in core["areas"]}
    lines = [f"- {names[a]}: {_placed(planets[k])}; today's {names[a]} score {scores[a]} out of 5"
             for a, k in AREA_PLANETS]
    return build_context(user, profile, day) + "\nPLANET CARDS (one per area, in the order of the output):\n" + "\n".join(lines)


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def parse_texts(raw: str) -> dict[str, dict[str, str]] | None:
    """The model's JSON, checked: all five areas, each with a headline and a message. None when it does not fit."""
    try:
        data = json.loads(_FENCE.sub("", raw.strip()))
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    out: dict[str, dict[str, str]] = {}
    for a in AREAS:
        v = data.get(a)
        if not isinstance(v, dict):
            return None
        h, m = v.get("headline"), v.get("message")
        if not (isinstance(h, str) and isinstance(m, str) and h.strip() and m.strip()):
            return None
        out[a] = {"headline": h.strip(), "message": m.strip()}
    return out


def _acceptable(raw: str) -> dict[str, dict[str, str]] | None:
    texts = parse_texts(raw)
    if texts is None or any(breaks_tone_rules(v["headline"] + " " + v["message"]) for v in texts.values()):
        return None
    return texts


def get_or_build_texts(db: Session, user: User, profile: BirthProfile, day: date, lang: str, client: LlmClient | None,
                       chart: dict, core: dict) -> DailyPlanetCards:
    found = saved(db, profile, day, lang)
    if found is not None:
        return found
    if client is None:
        raise LlmError("not configured")
    system = planet_cards_system_prompt(lang, _context(user, profile, day, chart, core))
    turns = [Turn("user", PLANET_CARDS_REQUEST)]
    result = client.generate(system, turns)
    texts = _acceptable(result.text)
    if texts is None:
        log.info("planet cards did not fit or broke tone rules; retrying once")
        result = client.generate(system + RETRY_NOTE, turns)
        texts = _acceptable(result.text)
    if texts is None:
        raise LlmError("planet cards")  # save nothing; the next open tries again
    row = DailyPlanetCards(user_id=user.id, profile_id=profile.id, local_date=day, lang=lang, texts=texts, status="draft",
                           model=result.model, tokens_in=result.tokens_in, tokens_out=result.tokens_out)
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


def get_or_build(db: Session, user: User, profile: BirthProfile, day: date, lang: str, client: LlmClient | None) -> list[dict]:
    """The five cards for the day. Raises love_reading.NeedsBirthTime (the house needs the birth time), or LlmError."""
    chart = love_reading.chart_for(profile)
    loc = day_location(user, profile)
    core = service.personal_card_core(profile, day, loc.latitude, loc.longitude, loc.timezone)
    row = get_or_build_texts(db, user, profile, day, lang, client, chart, core)
    planets = _placements(chart)
    scores = {a["key"]: a["score"] for a in core["areas"]}
    names = {a["key"]: a["name"] for a in core["areas"]}
    cards = []
    for area, key in AREA_PLANETS:
        p = planets[key]
        sign_name = names_pair(zodiac.SIGNS[p["sign"] - 1])
        m = chart_meanings.planet_meaning(key, p["sign"], sign_name, p["house"])
        cards.append({
            "area": area, "area_name": names[area], "planet": key, "planet_name": p["name"],
            "sign": {"number": p["sign"], **sign_name}, "house": p["house"], "dignity": p["dignity"],
            "retrograde": p["retrograde"], "score": scores[area],
            "headline": row.texts[area]["headline"], "message": row.texts[area]["message"],
            "meaning": {"in_sign": m.in_sign, "in_house": m.in_house} if m else None,
            "status": row.status,
        })
    return cards
