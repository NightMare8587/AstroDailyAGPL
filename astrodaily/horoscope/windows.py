"""Best and avoid time windows (muhurat) derived from panchang data."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

MIN_WINDOW_DURATION = timedelta(minutes=45)

# Lower rank number = higher priority.
BEST_RANK: dict[str, int] = {
    "Amrit": 0,
    "Abhijit Muhurat": 1,
    "Shubh": 2,
    "Labh": 3,
    "Char": 4,
}
AVOID_CHOGHADIYA: frozenset[str] = frozenset({"Kaal", "Rog", "Udveg"})

_BEST_REASONS: dict[str, str] = {
    "Amrit": "Amrit choghadiya is traditionally favoured for important and focused tasks.",
    "Abhijit Muhurat": "Abhijit Muhurat around solar noon supports decisive, constructive work.",
    "Shubh": "Shubh choghadiya favours steady progress, planning, and collaboration.",
    "Labh": "Labh choghadiya is well suited for practical gains, trade, and follow-through.",
    "Char": "Char choghadiya suits routine movement, errands, and adaptable tasks.",
}
_AVOID_REASONS: dict[str, str] = {
    "Rahu Kaal": "Rahu Kaal is best kept for routine work rather than major new starts.",
    "Kaal": "Daytime Kaal choghadiya favours maintenance over launching new commitments.",
    "Rog": "Daytime Rog choghadiya suggests pacing yourself and keeping tasks light.",
    "Udveg": "Daytime Udveg choghadiya favours calm routine over high-stakes decisions.",
}


@dataclass(frozen=True)
class Window:
    label: str
    start: datetime
    end: datetime
    reason: str


def _subtract_intervals(
    start: datetime,
    end: datetime,
    blocked: list[tuple[datetime, datetime]],
) -> list[tuple[datetime, datetime]]:
    pieces: list[tuple[datetime, datetime]] = [(start, end)]
    for b_start, b_end in sorted(blocked):
        next_pieces: list[tuple[datetime, datetime]] = []
        for p_start, p_end in pieces:
            if b_end <= p_start or b_start >= p_end:
                next_pieces.append((p_start, p_end))
            else:
                if p_start < b_start:
                    next_pieces.append((p_start, b_start))
                if b_end < p_end:
                    next_pieces.append((b_end, p_end))
        pieces = next_pieces
    return pieces


def _daytime_choghadiya(panchang: dict[str, Any]) -> list[Any]:
    """Return the daytime choghadiya slots (sunrise to sunset).

    Uses ``slot.start < sunset`` rather than ``slot.end <= sunset`` because ``split_segments``
    builds slot ends by multiplying a rounded ``timedelta``, which can put the 8th slot's end a
    few microseconds past ``sunset``.
    """
    sunset = panchang["sunset"]
    return [slot for slot in panchang["choghadiya"] if slot.start < sunset]


def best_windows(panchang: dict[str, Any], limit: int = 2) -> list[Window]:
    """Return up to ``limit`` top-ranked daytime windows (>= 45 min) free of Rahu/Gulika/Yamaganda.

    Daytime choghadiya slots (sunrise to sunset) in Amrit > Abhijit Muhurat > Shubh > Labh > Char
    are split around Rahu Kaal, Gulika Kaal, and Yamaganda; surviving pieces of at least 45
    minutes are sorted by rank then start time.
    """
    if limit <= 0:
        return []

    sunset = panchang["sunset"]
    blocked = [
        (panchang["rahu_kaal"].start, panchang["rahu_kaal"].end),
        (panchang["gulika_kaal"].start, panchang["gulika_kaal"].end),
        (panchang["yamaganda"].start, panchang["yamaganda"].end),
    ]

    candidates = [slot for slot in _daytime_choghadiya(panchang) if slot.en in BEST_RANK]
    candidates.append(panchang["abhijit"])

    ranked: list[tuple[tuple[int, datetime, datetime, str], Window]] = []
    for slot in candidates:
        slot_end = min(slot.end, sunset)
        for seg_start, seg_end in _subtract_intervals(slot.start, slot_end, blocked):
            if (seg_end - seg_start) >= MIN_WINDOW_DURATION:
                win = Window(
                    label=slot.en,
                    start=seg_start,
                    end=seg_end,
                    reason=_BEST_REASONS[slot.en],
                )
                sort_key = (BEST_RANK[slot.en], seg_start, seg_end, slot.en)
                ranked.append((sort_key, win))

    ranked.sort(key=lambda item: item[0])
    return [win for _, win in ranked[:limit]]


def avoid_windows(panchang: dict[str, Any]) -> list[Window]:
    """Return Rahu Kaal plus daytime Kaal, Rog, and Udveg choghadiya slots, deterministically sorted."""
    sunset = panchang["sunset"]
    rahu = panchang["rahu_kaal"]
    windows: list[Window] = [
        Window(label="Rahu Kaal", start=rahu.start, end=min(rahu.end, sunset), reason=_AVOID_REASONS["Rahu Kaal"])
    ]
    for slot in _daytime_choghadiya(panchang):
        if slot.en in AVOID_CHOGHADIYA:
            windows.append(Window(
                label=slot.en,
                start=slot.start,
                end=min(slot.end, sunset),
                reason=_AVOID_REASONS[slot.en],
            ))
    windows.sort(key=lambda w: (w.start, w.end, w.label))
    return windows
