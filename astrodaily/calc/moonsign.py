"""Find a person's Moon sign (janma rashi) from birth details, and say how sure we are.

With the exact birth time the Moon's sidereal (Lahiri) longitude gives the sign, nakshatra and pada.
With only the birth date the Moon can be in one sign all day, or change sign during it (it travels about
13 degrees a day, so a sign change happens on roughly 44% of days). Then there are two candidates.
"""
from dataclasses import dataclass
from datetime import date, time, timedelta, timezone

from . import ephem, zodiac
from .kundli import NAK_SPAN, resolve_birth_moment


@dataclass(frozen=True)
class MoonAtBirth:
    sign: int         # 1..12
    nakshatra: int    # 1..27
    pada: int         # 1..4
    longitude: float
    warnings: list[str]


def _moon_longitude(utc) -> float:
    return ephem.sidereal_longitude(ephem.datetime_to_jd(utc.astimezone(timezone.utc)), ephem.MOON)


def moon_at_birth(birth_date: date, birth_time: time, tz_name: str | None, utc_offset_minutes: int | None) -> MoonAtBirth:
    """The Moon at an exact birth moment."""
    birth = resolve_birth_moment(birth_date, birth_time, tz_name, utc_offset_minutes)
    lon = _moon_longitude(birth.utc)
    idx = int(lon // NAK_SPAN)
    pada = min(int((lon - idx * NAK_SPAN) / (NAK_SPAN / 4)) + 1, 4)
    return MoonAtBirth(zodiac.sign_of(lon), idx + 1, pada, lon, birth.warnings)


def candidate_signs(birth_date: date, tz_name: str | None, utc_offset_minutes: int | None) -> list[int]:
    """The Moon signs possible on a birth date when the time is unknown: one sign, or two in order
    (the Moon moves under 15 degrees a day, so it never crosses two sign boundaries in one day).

    The local day runs from its midnight to the next local midnight (a second before it), so a sign change in the very
    last minute counts, and so does a day that is longer or shorter because the clocks changed."""
    start = resolve_birth_moment(birth_date, time(0, 0), tz_name, utc_offset_minutes).utc
    next_midnight = resolve_birth_moment(birth_date + timedelta(days=1), time(0, 0), tz_name, utc_offset_minutes).utc
    first = zodiac.sign_of(_moon_longitude(start))
    last = zodiac.sign_of(_moon_longitude(next_midnight - timedelta(seconds=1)))
    return [first] if first == last else [first, last]
