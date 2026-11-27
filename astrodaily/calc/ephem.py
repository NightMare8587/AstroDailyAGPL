"""Thin wrapper over Swiss Ephemeris (pyswisseph), sidereal Lahiri.

Uses the built-in Moshier ephemeris unless an ephemeris folder is configured.

Swiss Ephemeris keeps its settings (sidereal mode, ephemeris path) in global state that, on some
builds (the Linux one compiled on Railway), is per thread. A setting made once at start-up is then
invisible to the web server's worker threads, which silently fall back to the default ayanamsa
(Fagan-Bradley, about 0.9 degrees off Lahiri). So every calculation re-applies the settings itself.
"""
from datetime import datetime, timedelta, timezone

import swisseph as swe

UNIX_EPOCH_JD = 2440587.5
SUN = swe.SUN
MOON = swe.MOON
MARS = swe.MARS
MERCURY = swe.MERCURY
JUPITER = swe.JUPITER
VENUS = swe.VENUS
SATURN = swe.SATURN
MEAN_NODE = swe.MEAN_NODE
TRUE_NODE = swe.TRUE_NODE

_base_flags = swe.FLG_MOSEPH
_ephe_path: str | None = None
LAHIRI_J2000 = 23.857  # degrees, approximately, at 2000-01-01 12:00 UT


def configure(ephemeris_path: str | None = None) -> None:
    global _base_flags, _ephe_path
    _ephe_path = ephemeris_path or None
    _base_flags = swe.FLG_SWIEPH if _ephe_path else swe.FLG_MOSEPH
    _prepare()


def _prepare() -> None:
    """Apply the settings in the calling thread. Cheap, and safe to call every time."""
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    if _ephe_path:
        swe.set_ephe_path(_ephe_path)


def datetime_to_jd(dt: datetime) -> float:
    return dt.timestamp() / 86400.0 + UNIX_EPOCH_JD


def jd_to_datetime(jd: float, tz) -> datetime:
    utc = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(days=jd - UNIX_EPOCH_JD)
    return utc.astimezone(tz)


def sidereal_longitude(jd_ut: float, body: int) -> float:
    _prepare()
    xx, _ = swe.calc_ut(jd_ut, body, _base_flags | swe.FLG_SIDEREAL)
    return xx[0] % 360.0


def ayanamsa(jd_ut: float) -> float:
    _prepare()
    return swe.get_ayanamsa_ut(jd_ut)


def _rise_set(jd_start: float, lat: float, lon: float, rsmi: int) -> float:
    _prepare()
    res, tret = swe.rise_trans(
        jd_start, swe.SUN, rsmi, (lon, lat, 0.0), 1013.25, 15.0, _base_flags
    )
    if res != 0:
        raise ValueError("Sun does not rise or set at this location on this date")
    return tret[0]


def next_sunrise(jd_start: float, lat: float, lon: float) -> float:
    return _rise_set(jd_start, lat, lon, swe.CALC_RISE)


def next_sunset(jd_start: float, lat: float, lon: float) -> float:
    return _rise_set(jd_start, lat, lon, swe.CALC_SET)


def body_position(jd_ut: float, body: int) -> tuple[float, float]:
    """(sidereal longitude in degrees, speed in degrees per day; negative = retrograde)."""
    _prepare()
    xx, _ = swe.calc_ut(jd_ut, body, _base_flags | swe.FLG_SIDEREAL | swe.FLG_SPEED)
    return xx[0] % 360.0, xx[3]


def ascendant(jd_ut: float, lat: float, lon: float) -> float:
    """Sidereal longitude of the ascendant (lagna)."""
    _prepare()
    _, ascmc = swe.houses_ex(jd_ut, lat, lon, b"W", swe.FLG_SIDEREAL)
    return ascmc[0] % 360.0


def self_check() -> tuple[bool, float]:
    """(ok, ayanamsa) for a known date, computed in the calling thread. Catches a wrong sidereal mode."""
    jd = 2451545.0
    value = ayanamsa(jd)
    return abs(value - LAHIRI_J2000) < 0.01, value
