"""Pure daily horoscope calculation engine (phase 1)."""
from .report import ENGINE_VERSION, DayReport, Windows, build_day_report
from .rules import RULESET_VERSION
from .scoring import area_scores, day_score
from .selection import Selection, select
from .signals import DayContext, NatalContext, Signal, evaluate_signals, natal_from_chart
from .weights import AREAS, SCORING_VERSION
from .windows import Window, avoid_windows, best_windows

__all__ = [
    "AREAS",
    "ENGINE_VERSION",
    "RULESET_VERSION",
    "SCORING_VERSION",
    "DayContext",
    "DayReport",
    "NatalContext",
    "Selection",
    "Signal",
    "Window",
    "Windows",
    "area_scores",
    "avoid_windows",
    "best_windows",
    "build_day_report",
    "day_score",
    "evaluate_signals",
    "natal_from_chart",
    "select",
]
