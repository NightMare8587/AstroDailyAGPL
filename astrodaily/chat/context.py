"""The facts the model may use, computed by the engine. Derived facts only: no name, email, birth date,
birth time or coordinates are included."""
from datetime import date, datetime, time, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

from ..calc import names, yogas, zodiac
from ..calc.kundli import compute_chart, resolve_birth_moment
from ..content import yoga_text
from ..horoscope import love_reading, service
from ..horoscope.signals import natal_from_chart
from ..models import BirthProfile, User


@lru_cache(maxsize=1024)
def _natal(birth_date: date, birth_time: time, lat: float, lon: float, tz: str, offset: int | None, day: date):
    birth = resolve_birth_moment(birth_date, birth_time, tz, offset)
    noon = datetime.combine(day, time(12, 0), tzinfo=timezone.utc)
    return natal_from_chart(compute_chart(birth, lat, lon, "mean", noon), as_of=noon)


def day_location(user: User, p: BirthProfile) -> service.DayLocation:
    h = user.home_place
    if h is not None:
        return service.DayLocation(h.latitude, h.longitude, h.timezone, h.name, "home")
    return service.DayLocation(p.latitude, p.longitude, p.timezone, p.place_name, "profile")


def _hm(value: datetime, tz: str) -> str:
    return value.astimezone(ZoneInfo(tz)).strftime("%H:%M")


def chart_lines(p: BirthProfile) -> list[str]:
    """The birth chart as plain facts: where each planet sits and how strongly, the yogas and doshas that are present,
    and the partnership facts the love reading uses. Needs the birth time. Derived facts only (no degrees or dates)."""
    chart = love_reading.chart_for(p)
    sun_lon = next(x["longitude"] for x in chart["planets"] if x["key"] == "Sun")
    placed = []
    for x in chart["planets"]:
        notes = [f"house {x['house']}"]
        if x["dignity"]:
            notes.append(x["dignity"])
        if x["retrograde"]:
            notes.append("retrograde")
        notes.append(yoga_text.LEVELS[yogas.strength(x, sun_lon)["level"]][0].lower() + " position")
        placed.append(f"{x['key']} in {zodiac.SIGNS[x['sign'] - 1][0]} ({', '.join(notes)})")
    present = {y["key"]: y for y in yogas.detect(chart, chart["dasha"]["as_of"])}
    mars = next(x for x in chart["planets"] if x["key"] == "Mars")
    mangal = ("Mangal dosha (being manglik), by Brihat Parashara Hora Shastra 80.47 (Mars in house 1, 4, 7, 8 or 12 from the "
              "lagna, unless Jupiter or Venus joins or aspects it): " + ("present" if "mangal_dosha" in present else "NOT present")
              + f"; Mars is in house {mars['house']}.")
    if mars["house"] == 2:
        mangal += (" Some other texts (Jataka Parijata 14.34, B. V. Raman's Muhurtha) also count the 2nd house, so by those "
                   "it would count as a milder dosha; the answer depends on which text is followed.")
    others = {k: v["name"][0] for k, v in yoga_text.TEXT.items() if k != "mangal_dosha"}
    lines = [
        "CHART (derived; rules are common convention, not verified): " + "; ".join(placed) + ".",
        mangal,
        "Other yogas and doshas present: " + (", ".join(others[k] + (f" ({', '.join(present[k]['planets'])})" if present[k]["planets"] else "")
                                                       for k in others if k in present) or "none") + ". Checked and not present: "
        + (", ".join(n for k, n in others.items() if k not in present) or "none") + ".",
        "PARTNERSHIP: " + " ".join(love_reading.facts(chart).splitlines()),
    ]
    return lines


def build_context(user: User, p: BirthProfile, day: date | None = None) -> str:
    loc = day_location(user, p)
    day = day or service.today_in(loc.timezone)
    core = service.personal_card_core(p, day, loc.latitude, loc.longitude, loc.timezone)
    pan = core["panchang"]
    if p.birth_time is None:
        # No birth time: only the Moon sign is known, so there is no birth star, ascendant or running period.
        person = (f"Moon sign (rashi) {zodiac.SIGNS[p.moon_sign - 1][0]}; birth time unknown, so the birth star, "
                  "ascendant and running period are not known (do not guess them).")
    else:
        natal = _natal(p.birth_date, p.birth_time, p.latitude, p.longitude, p.timezone, p.utc_offset_minutes, day)
        dasha = natal.running_dasha or {}
        person = (f"Moon sign (rashi) {zodiac.SIGNS[natal.moon_sign - 1][0]}; "
                  f"birth star (nakshatra) {names.NAKSHATRA[natal.moon_nakshatra - 1][0]}; "
                  f"ascendant (lagna) {zodiac.SIGNS[natal.lagna_sign - 1][0]}; "
                  f"running period (Vimshottari dasha) {dasha.get('mahadasha', 'unknown')} / {dasha.get('antardasha', 'unknown')}.")
    lines = [
        f"DATE: {day.isoformat()} ({pan['vara']['en']}), city: {loc.place_name or 'unknown'}.",
        "PERSON (derived facts only): " + person,
        f"TODAY: day score {core['score']} out of 5 (1 = go easy, 5 = very supportive). Area scores, also out of 5: "
        + ", ".join(f"{a['name']['en']} {a['score']}" for a in core["areas"]) + ".",
        "Suits today: " + (" | ".join(s["reason"] for s in core["dos"]) or "nothing notable") + ".",
        "Go easy on: " + (" | ".join(s["reason"] for s in core["donts"]) or "nothing notable") + ".",
    ]
    if p.birth_time is not None:
        lines += chart_lines(p)
    if core["theme"]:
        lines.append("Theme: " + core["theme"]["reason"])
    if core["coming_up"]:
        lines.append("Coming up: " + core["coming_up"]["reason"])
    w = core["windows"]
    lines.append("Good times today: " + (", ".join(f"{x['label']} {_hm(x['start'], loc.timezone)}-{_hm(x['end'], loc.timezone)}"
                                                for x in w["best"]) or "none listed") + ".")
    lines.append("Times to go easy: " + (", ".join(f"{x['label']} {_hm(x['start'], loc.timezone)}-{_hm(x['end'], loc.timezone)}"
                                                for x in w["avoid"]) or "none listed") + ".")
    lines.append(f"Panchang: tithi {pan['tithi']['en']} ({pan['tithi'].get('paksha')} paksha), nakshatra "
                 f"{pan['nakshatra']['en']}, yoga {pan['yoga']['en']}, karana {pan['karana']['en']}.")
    return "\n".join(lines)
