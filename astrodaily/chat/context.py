"""The facts the model may use, computed by the engine. Derived facts only: no name, email, birth date,
birth time or coordinates are included."""
from datetime import date, datetime, time, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

from ..calc import names, zodiac
from ..calc.kundli import compute_chart, resolve_birth_moment
from ..horoscope import service
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


def build_context(user: User, p: BirthProfile, day: date | None = None) -> str:
    loc = day_location(user, p)
    day = day or service.today_in(loc.timezone)
    core = service.profile_card_core(p.birth_date, p.birth_time, p.latitude, p.longitude, p.timezone,
                                     p.utc_offset_minutes, day, loc.latitude, loc.longitude, loc.timezone)
    natal = _natal(p.birth_date, p.birth_time, p.latitude, p.longitude, p.timezone, p.utc_offset_minutes, day)
    pan = core["panchang"]
    dasha = natal.running_dasha or {}
    lines = [
        f"DATE: {day.isoformat()} ({pan['vara']['en']}), city: {loc.place_name or 'unknown'}.",
        "PERSON (derived facts only): "
        f"Moon sign (rashi) {zodiac.SIGNS[natal.moon_sign - 1][0]}; "
        f"birth star (nakshatra) {names.NAKSHATRA[natal.moon_nakshatra - 1][0]}; "
        f"ascendant (lagna) {zodiac.SIGNS[natal.lagna_sign - 1][0]}; "
        f"running period (Vimshottari dasha) {dasha.get('mahadasha', 'unknown')} / {dasha.get('antardasha', 'unknown')}.",
        f"TODAY: day score {core['score']} out of 5 (1 = go easy, 5 = very supportive). Area scores, also out of 5: "
        + ", ".join(f"{a['name']['en']} {a['score']}" for a in core["areas"]) + ".",
        "Suits today: " + (" | ".join(s["reason"] for s in core["dos"]) or "nothing notable") + ".",
        "Go easy on: " + (" | ".join(s["reason"] for s in core["donts"]) or "nothing notable") + ".",
    ]
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
