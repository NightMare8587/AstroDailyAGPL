"""Compute daily horoscope cards. Pure and deterministic; results are kept in a small in-process
cache (nothing is stored in the database).

Why no database cache: the engine takes about 4 ms per card, so a table would add storage, a
migration and a way for anonymous callers to fill it by varying coordinates, for no real speed
gain. Revisit when generated text (slow, costly) exists.
"""
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from functools import lru_cache
from typing import Any
from zoneinfo import ZoneInfo

from ..calc.kundli import compute_chart, resolve_birth_moment
from ..calc.panchang import compute_panchang
from .card import build_card
from .report import build_day_report
from .signals import NatalContext, natal_from_chart

CACHE_SIZE = 4096


@dataclass(frozen=True)
class DayLocation:
    latitude: float
    longitude: float
    timezone: str
    place_name: str | None
    source: str  # explicit_place, coordinates, home, profile or default


DEFAULT_LOCATION = DayLocation(28.6139, 77.2090, "Asia/Kolkata", "New Delhi (default)", "default")


def today_in(tz_name: str) -> date:
    return datetime.now(ZoneInfo(tz_name)).date()


@lru_cache(maxsize=CACHE_SIZE)
def rashi_card_core(rashi: int, day: date, lat: float, lon: float, tz: str) -> dict[str, Any]:
    """Level A card for a Moon sign (1..12). No birth details needed."""
    panchang = compute_panchang(day, lat, lon, tz)
    report = build_day_report(day, lat, lon, tz, NatalContext(moon_sign=rashi))
    return build_card(report, panchang)


@lru_cache(maxsize=CACHE_SIZE)
def profile_card_core(
    birth_date: date, birth_time: time, birth_lat: float, birth_lon: float, birth_tz: str,
    birth_offset: int | None, day: date, lat: float, lon: float, tz: str,
) -> dict[str, Any]:
    """Level B card for one person: their natal Moon, nakshatra, lagna and running dasha, today's sky
    at the card's location. The cache key holds the birth details, so editing a profile can never serve a
    stale card."""
    birth = resolve_birth_moment(birth_date, birth_time, birth_tz, birth_offset)
    noon_utc = datetime.combine(day, time(12, 0), tzinfo=ZoneInfo(tz)).astimezone(timezone.utc)
    chart = compute_chart(birth, birth_lat, birth_lon, "mean", noon_utc)
    natal = natal_from_chart(chart, as_of=noon_utc)
    panchang = compute_panchang(day, lat, lon, tz)
    report = build_day_report(day, lat, lon, tz, natal)
    return build_card(report, panchang)


def with_location(core: dict[str, Any], loc: DayLocation) -> dict[str, Any]:
    """Attach the location without touching the cached dict."""
    return {**core, "location": {
        "latitude": loc.latitude, "longitude": loc.longitude, "timezone": loc.timezone,
        "place_name": loc.place_name, "source": loc.source,
    }}
