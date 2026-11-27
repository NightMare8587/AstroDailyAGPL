"""Area and overall day scoring from horoscope signals."""
from collections.abc import Sequence

from . import weights
from .signals import Signal


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _map_area_score(total: float) -> int:
    lo, hi = weights.AREA_CLIP
    clipped = _clip(total, lo, hi)
    t0, t1, t2, t3 = weights.AREA_THRESHOLDS
    if clipped < t0:
        return 1
    if clipped < t1:
        return 2
    if clipped <= t2:
        return 3
    if clipped <= t3:
        return 4
    return 5


def area_scores(signals: Sequence[Signal]) -> dict[str, int]:
    """Sum signal weights per area, subtract one-sided rule baseline drift, clip, and map to 1..5.

    Two-outcome rule families (Chandra Bala, Gochara, Tara Bala) have zero long-run expectation
    baked into ``weights.WEIGHTS``. One-sided negative families (Saturn cycles and Panchang
    day-quality penalties) have negative expected values; when those rule families were evaluated
    (detected by the presence of ``vara_*`` for Panchang and ``chandra_bala_*`` for natal
    transits/Saturn cycles), their exact rule-table expectation from ``weights`` is subtracted so
    the long-run average remains centred at 3. Neutral input (no signals, or synthetic signals
    without those rule families) receives no offset and maps 0.0 to 3 everywhere.
    """
    totals = {area: 0.0 for area in weights.AREAS}
    has_panchang = False
    has_natal_transits = False
    for signal in signals:
        if signal.id.startswith("vara_"):
            has_panchang = True
        elif signal.id.startswith("chandra_bala_"):
            has_natal_transits = True
        for area in weights.AREAS:
            totals[area] += float(signal.weights.get(area, 0.0))

    if has_panchang:
        panchang_drift = weights.expected_panchang_drift()
        for area in weights.AREAS:
            totals[area] -= panchang_drift[area]
    if has_natal_transits:
        saturn_drift = weights.expected_saturn_cycle_drift()
        for area in weights.AREAS:
            totals[area] -= saturn_drift[area]

    return {area: _map_area_score(totals[area]) for area in weights.AREAS}


def day_score(areas: dict[str, int], signals: Sequence[Signal]) -> int:
    """Compute overall day score (1..5) as the rounded half-up mean of the five area scores.

    With baseline-centred weights and symmetric thresholds, area scores are balanced around 3 so
    no artificial floor is needed (removing any positive skew while keeping rare extreme days
    symmetric between 1 and 5).
    """
    del signals  # kept in signature for API stability
    values = [areas[area] for area in weights.AREAS] if all(a in areas for a in weights.AREAS) else list(areas.values())
    if not values:
        return 3
    mean = sum(values) / len(values)
    return max(1, min(5, int(mean + 0.5)))
