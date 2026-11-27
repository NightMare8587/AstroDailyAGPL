"""Planetary transit positions, sign ingresses, and Saturn cycle helpers (sidereal Lahiri).

Uses only the helpers in ``astrodaily.calc.ephem`` so Swiss Ephemeris settings are re-applied per
call in every worker thread. Rahu uses the mean node and Ketu is opposite (Rahu + 180 deg), matching
``astrodaily.calc.kundli``.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

from . import ephem, zodiac

GRAHAS: tuple[tuple[str, int], ...] = (
    ("Sun", ephem.SUN),
    ("Moon", ephem.MOON),
    ("Mars", ephem.MARS),
    ("Mercury", ephem.MERCURY),
    ("Jupiter", ephem.JUPITER),
    ("Venus", ephem.VENUS),
    ("Saturn", ephem.SATURN),
)
_BODY_BY_KEY: dict[str, int] = dict(GRAHAS)
ALL_GRAHAS: tuple[str, ...] = tuple(k for k, _ in GRAHAS) + ("Rahu", "Ketu")

SaturnState = Literal["rising", "peak", "setting", "ashtama", "ardhashtama"]


@dataclass(frozen=True)
class GrahaTransit:
    key: str
    longitude: float  # sidereal 0..360
    sign: int         # 1..12
    retrograde: bool  # Rahu/Ketu always True (as in kundli.py)


@dataclass(frozen=True)
class Ingress:
    key: str
    when: datetime    # UTC tz-aware
    from_sign: int    # 1..12
    to_sign: int      # 1..12


def _validate_sign(sign: int, label: str = "sign") -> None:
    if not 1 <= sign <= 12:
        raise ValueError(f"{label} must be in 1..12, got {sign}")


def house_from(sign: int, reference_sign: int) -> int:
    """Whole-sign house (1..12) of ``sign`` counted from ``reference_sign`` (house 1)."""
    _validate_sign(sign, "sign")
    _validate_sign(reference_sign, "reference_sign")
    return (sign - reference_sign) % 12 + 1


def transit_positions(jd_ut: float) -> dict[str, GrahaTransit]:
    """Sidereal positions and retrograde flags for all nine grahas at Julian day ``jd_ut``."""
    out: dict[str, GrahaTransit] = {}
    for key, body in GRAHAS:
        lon, speed = ephem.body_position(jd_ut, body)
        out[key] = GrahaTransit(key=key, longitude=lon, sign=zodiac.sign_of(lon), retrograde=speed < 0)

    rahu_lon, _ = ephem.body_position(jd_ut, ephem.MEAN_NODE)
    ketu_lon = (rahu_lon + 180.0) % 360.0
    # Nodes are conventionally treated as always retrograde, matching kundli.py.
    out["Rahu"] = GrahaTransit(key="Rahu", longitude=rahu_lon, sign=zodiac.sign_of(rahu_lon), retrograde=True)
    out["Ketu"] = GrahaTransit(key="Ketu", longitude=ketu_lon, sign=zodiac.sign_of(ketu_lon), retrograde=True)
    return out


def _graha_sign(key: str, jd_ut: float) -> int:
    if key in _BODY_BY_KEY:
        lon = ephem.sidereal_longitude(jd_ut, _BODY_BY_KEY[key])
    elif key == "Rahu":
        lon = ephem.sidereal_longitude(jd_ut, ephem.MEAN_NODE)
    elif key == "Ketu":
        lon = (ephem.sidereal_longitude(jd_ut, ephem.MEAN_NODE) + 180.0) % 360.0
    else:
        raise ValueError(f"Unknown graha key: {key!r}")
    return zodiac.sign_of(lon)


def next_ingress(key: str, after: datetime, within_days: float = 30.0) -> Ingress | None:
    """First sign change for ``key`` after ``after`` (tz-aware) within ``within_days``, or None.

    Scans with a 6-hour step (small enough that even the Moon moves ~3.3 deg and cannot skip a
    30-deg sign) and bisects the crossing bracket to sub-second precision. Works identically for
    direct and retrograde sign changes.
    """
    if after.tzinfo is None:
        raise ValueError("after must be timezone-aware")
    if key not in ALL_GRAHAS:
        raise ValueError(f"Unknown graha key: {key!r}")
    if within_days <= 0:
        return None

    jd_start = ephem.datetime_to_jd(after.astimezone(timezone.utc))
    jd_end = jd_start + within_days
    start_sign = _graha_sign(key, jd_start)

    step_days = 0.25  # 6 hours
    lo = jd_start
    while lo < jd_end:
        hi = min(lo + step_days, jd_end)
        end_sign = _graha_sign(key, hi)
        if end_sign != start_sign:
            b_lo, b_hi = lo, hi
            # 16 bisections on <= 6h bracket gives < 0.4 second precision (well within 1 minute).
            for _ in range(16):
                mid = (b_lo + b_hi) / 2.0
                if _graha_sign(key, mid) == start_sign:
                    b_lo = mid
                else:
                    b_hi = mid
            when = ephem.jd_to_datetime(b_hi, timezone.utc)
            if when <= after.astimezone(timezone.utc):
                when = after.astimezone(timezone.utc) + timedelta(seconds=1)
            return Ingress(key=key, when=when, from_sign=start_sign, to_sign=_graha_sign(key, b_hi))
        lo = hi
    return None


def sade_sati_state(natal_moon_sign: int, saturn_sign: int) -> SaturnState | None:
    """Return Saturn's transit cycle relative to the natal Moon sign, or None."""
    house = house_from(saturn_sign, natal_moon_sign)
    return {
        12: "rising",
        1: "peak",
        2: "setting",
        8: "ashtama",
        4: "ardhashtama",
    }.get(house)
