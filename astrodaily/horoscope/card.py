"""Turn an engine DayReport into the plain-data card the API returns.

Phase 3 has no content library yet, so the wording is the engine's own English ``reason`` strings
(calm and practical by construction). A content library will replace them later without changing
the shape.
"""
from datetime import date, datetime
from typing import Any

from .report import DayReport
from .signals import Signal
from .weights import AREAS, SCORING_VERSION
from .windows import Window

AREA_NAMES: dict[str, tuple[str, str]] = {
    "career": ("Career", "करियर"),
    "money": ("Money", "धन"),
    "relationships": ("Relationships", "संबंध"),
    "health": ("Health and energy", "स्वास्थ्य और ऊर्जा"),
    "mind": ("Mind and learning", "मन और सीख"),
}

DISCLAIMER = {
    "en": "For reflection only. Not medical, legal or financial advice.",
    "hi": "यह केवल चिंतन के लिए है। यह चिकित्सा, कानूनी या वित्तीय सलाह नहीं है।",
}


def json_safe(value: Any) -> Any:
    """Make engine params serialisable: tuples and sets become lists, dates become ISO strings."""
    if isinstance(value, (list, tuple, set, frozenset)):
        return [json_safe(v) for v in (sorted(value) if isinstance(value, (set, frozenset)) else value)]
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def signal_card(signal: Signal) -> dict[str, Any]:
    return {
        "id": signal.id,
        "kind": signal.kind,
        "scope": signal.scope,
        "reason": signal.reason,
        "params": json_safe(signal.params),
    }


def window_card(window: Window) -> dict[str, Any]:
    return {"label": window.label, "start": window.start, "end": window.end, "reason": window.reason}


def panchang_brief(panchang: dict[str, Any]) -> dict[str, Any]:
    def element(e: Any) -> dict[str, Any]:
        return {"number": e.number, "en": e.en, "hi": e.hi, "ends_at": e.ends_at}

    return {
        "sunrise": panchang["sunrise"],
        "sunset": panchang["sunset"],
        "vara": {"en": panchang["vara"][0], "hi": panchang["vara"][1]},
        "tithi": {**element(panchang["tithi"]), "paksha": panchang["tithi"].extra.get("paksha")},
        "nakshatra": element(panchang["nakshatra"]),
        "yoga": element(panchang["yoga"]),
        "karana": element(panchang["karana"]),
    }


def build_card(report: DayReport, panchang: dict[str, Any]) -> dict[str, Any]:
    """The day's card without location details (the caller adds those, so the core can be cached)."""
    return {
        "date": report.date,
        "level": report.level,
        "score": report.score,
        "areas": [
            {"key": a, "name": {"en": AREA_NAMES[a][0], "hi": AREA_NAMES[a][1]}, "score": report.areas[a]}
            for a in AREAS
        ],
        "dos": [signal_card(s) for s in report.favourable],
        "donts": [signal_card(s) for s in report.unfavourable],
        "theme": signal_card(report.theme) if report.theme else None,
        "coming_up": signal_card(report.coming_up) if report.coming_up else None,
        "windows": {
            "best": [window_card(w) for w in report.windows.best],
            "avoid": [window_card(w) for w in report.windows.avoid],
        },
        "why": [signal_card(s) for s in report.signals],
        "panchang": panchang_brief(panchang),
        "engine_version": report.engine_version,
        "ruleset_version": report.ruleset_version,
        "scoring_version": SCORING_VERSION,
        "generated_by": "rules",
    }
