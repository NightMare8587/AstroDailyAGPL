"""Top-level pure day report assembly."""
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from datetime import date
from typing import Literal

from astrodaily.calc import ephem
from astrodaily.calc.panchang import compute_panchang
from astrodaily.calc.transits import transit_positions
from . import rules
from .scoring import area_scores, day_score
from .selection import select
from .signals import DayContext, NatalContext, Signal, evaluate_signals
from .windows import Window, avoid_windows, best_windows

ENGINE_VERSION = "0.1"


@dataclass(frozen=True)
class Windows:
    best: list[Window]
    avoid: list[Window]


@dataclass(frozen=True)
class DayReport:
    date: date
    level: Literal["A", "B"]
    score: int
    areas: dict[str, int]
    favourable: list[Signal]
    unfavourable: list[Signal]
    theme: Signal | None
    coming_up: Signal | None
    windows: Windows
    signals: list[Signal]
    engine_version: str
    ruleset_version: str


def _report_level(natal: NatalContext | None) -> Literal["A", "B"]:
    if natal is None:
        return "A"
    if natal.moon_nakshatra is not None or natal.lagna_sign is not None or natal.running_dasha is not None:
        return "B"
    return "A"


def build_day_report(
    day: date,
    lat: float,
    lon: float,
    tz_name: str,
    natal: NatalContext | None = None,
    recently_shown: AbstractSet[str] = frozenset(),
) -> DayReport:
    """Compute a deterministic daily horoscope report for ``day`` and place, optionally personalised."""
    panchang = compute_panchang(day, lat, lon, tz_name)
    jd_sunrise = ephem.datetime_to_jd(panchang["sunrise"])
    transits = transit_positions(jd_sunrise)

    day_ctx = DayContext(date=day, panchang=panchang, transits=transits)
    signals = evaluate_signals(day_ctx, natal)
    areas = area_scores(signals)
    score = day_score(areas, signals)
    chosen = select(signals, recently_shown=recently_shown)
    win = Windows(best=best_windows(panchang), avoid=avoid_windows(panchang))

    return DayReport(
        date=day,
        level=_report_level(natal),
        score=score,
        areas=areas,
        favourable=chosen.favourable,
        unfavourable=chosen.unfavourable,
        theme=chosen.theme,
        coming_up=chosen.coming_up,
        windows=win,
        signals=signals,
        engine_version=ENGINE_VERSION,
        ruleset_version=rules.RULESET_VERSION,
    )
