"""Select the top signals for the daily card, breaking ties by freshness and id."""
from collections.abc import Sequence, Set as AbstractSet
from dataclasses import dataclass

from .signals import Signal


@dataclass(frozen=True)
class Selection:
    favourable: list[Signal]
    unfavourable: list[Signal]
    theme: Signal | None
    coming_up: Signal | None


def _sort_key(
    signal: Signal,
    recently_shown: AbstractSet[str],
    *,
    prefer_daily: bool = False,
) -> tuple[int, float, int, str]:
    scope_rank = 0 if (not prefer_daily or signal.scope == "daily") else 1
    strength = round(abs(sum(signal.weights.values())), 9)
    seen_penalty = 1 if signal.id in recently_shown else 0
    return (scope_rank, -strength, seen_penalty, signal.id)


def select(
    signals: Sequence[Signal],
    recently_shown: AbstractSet[str] = frozenset(),
) -> Selection:
    """Choose up to 3 favourable, up to 3 unfavourable, 1 theme, and at most 1 coming_up signal.

    For favourable and unfavourable lists, ``daily`` signals are picked first (strongest first,
    breaking ties by freshness then id) and ``standing`` signals are used only to fill remaining
    slots up to 3.
    """
    fav = sorted(
        (s for s in signals if s.kind == "favourable"),
        key=lambda s: _sort_key(s, recently_shown, prefer_daily=True),
    )[:3]
    unfav = sorted(
        (s for s in signals if s.kind == "unfavourable"),
        key=lambda s: _sort_key(s, recently_shown, prefer_daily=True),
    )[:3]
    themes = sorted(
        (s for s in signals if s.kind == "theme"),
        key=lambda s: _sort_key(s, recently_shown),
    )
    coming = sorted(
        (s for s in signals if s.kind == "coming_up"),
        key=lambda s: _sort_key(s, recently_shown),
    )
    return Selection(
        favourable=fav,
        unfavourable=unfav,
        theme=themes[0] if themes else None,
        coming_up=coming[0] if coming else None,
    )
