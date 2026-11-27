"""Thin wrapper over Swiss Ephemeris (pyswisseph), sidereal Lahiri.

Uses the built-in Moshier ephemeris unless an ephemeris folder is configured.
Swiss Ephemeris keeps global state, so configure() is called once at start-up.
"""
from datetime import datetime, timedelta, timezone

import swisseph as swe

UNIX_EPOCH_JD = 2440587.5
SUN = swe.SUN
MOON = swe.MOON

_base_flags = swe.FLG_MOSEPH


def configure(ephemeris_path: str | None = None) -> None:
    global _base_flags
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    if ephemeris_path:
        swe.set_ephe_path(ephemeris_path)
        _base_flags = swe.FLG_SWIEPH
    else:
        _base_flags = swe.FLG_MOSEPH


def datetime_to_jd(dt: datetime) -> float:
    return dt.timestamp() / 86400.0 + UNIX_EPOCH_JD


def jd_to_datetime(jd: float, tz) -> datetime:
    utc = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(days=jd - UNIX_EPOCH_JD)
    return utc.astimezone(tz)


def sidereal_longitude(jd_ut: float, body: int) -> float:
    xx, _ = swe.calc_ut(jd_ut, body, _base_flags | swe.FLG_SIDEREAL)
    return xx[0] % 360.0


def ayanamsa(jd_ut: float) -> float:
    return swe.get_ayanamsa_ut(jd_ut)


def _rise_set(jd_start: float, lat: float, lon: float, rsmi: int) -> float:
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
