"""Tunable weights and scoring thresholds for the daily horoscope engine.

Kept as pure Python data so weights and scoring bands can be tuned (or monkeypatched in tests)
without changing rule or scoring logic. All area weights stay in [-2.0, 2.0].

Centring method:
- Symmetric/two-outcome rule families (Chandra Bala, every Gochara planet, Tara Bala) have their
  per-signal weights centred in this module so each family's expected contribution per area under
  a uniform house/nakshatra distribution is 0.0.
- One-sided rule families that only emit negative signals (Saturn standing cycles in 5/12 houses;
  Panchang day-quality penalties at their natural frequencies 3/15 rikta, 1/30 amavasya, 8/60
  Vishti, 7/27 inauspicious yogas) expose ``expected_saturn_cycle_drift()`` and
  ``expected_panchang_drift()`` computed directly from ``WEIGHTS`` and ``rules``. ``area_scores``
  subtracts those drifts when those rule families were evaluated.
"""
from . import rules

AREAS: list[str] = ["career", "money", "relationships", "health", "mind"]

SCORING_VERSION = "0.2"

# Sum of weights per area is clipped to AREA_CLIP before mapping to 1..5 via AREA_THRESHOLDS.
AREA_CLIP: tuple[float, float] = (-4.0, 4.0)
# Symmetric thresholds around 0.0:
# score 1 if s < -t1, 2 if -t1 <= s < -t0, 3 if -t0 <= s <= t0, 4 if t0 < s <= t1, 5 if s > t1.
AREA_THRESHOLDS: tuple[float, float, float, float] = (-2.2, -0.70, 0.70, 2.2)

# Natural frequencies used to compute expected drift of one-sided rules from the rule tables.
SATURN_CYCLE_KEYS: tuple[str, ...] = (
    "sade_sati_rising",
    "sade_sati_peak",
    "sade_sati_setting",
    "ashtama_shani",
    "kantaka_shani",
)
PANCHANG_FREQUENCIES: dict[str, float] = {
    "rikta_tithi": 3.0 / 15.0,
    "amavasya": 1.0 / 30.0,
    "vishti_karana": 8.0 / 60.0,
    "inauspicious_yoga": len(rules.INAUSPICIOUS_YOGAS) / 27.0,
}


def _neg_scaled(good_row: dict[str, float], good_count: int, total: int = 12) -> dict[str, float]:
    """Return the exact zero-mean counterpart weights for ``total - good_count`` poor houses."""
    scale = good_count / (total - good_count)
    return {area: -scale * val for area, val in good_row.items()}


def _centre_rows(rows: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    """Subtract the per-area mean across ``rows`` so a uniform pick has 0.0 expectation."""
    n = len(rows)
    means = {area: sum(row[area] for row in rows.values()) / n for area in AREAS}
    return {
        key: {area: val - means[area] for area, val in row.items()}
        for key, row in rows.items()
    }


_CHANDRA_GOOD = {"career": 0.35, "money": 0.30, "relationships": 0.45, "health": 0.35, "mind": 0.55}

_TARA_RAW: dict[str, dict[str, float]] = {
    "tara_janma": {"career": -0.05, "money": -0.05, "relationships": -0.05, "health": -0.15, "mind": -0.15},
    "tara_sampat": {"career": 0.30, "money": 0.45, "relationships": 0.20, "health": 0.15, "mind": 0.25},
    "tara_vipat": {"career": -0.35, "money": -0.40, "relationships": -0.20, "health": -0.25, "mind": -0.35},
    "tara_kshema": {"career": 0.25, "money": 0.20, "relationships": 0.25, "health": 0.40, "mind": 0.35},
    "tara_pratyak": {"career": -0.35, "money": -0.20, "relationships": -0.35, "health": -0.20, "mind": -0.30},
    "tara_sadhana": {"career": 0.45, "money": 0.30, "relationships": 0.20, "health": 0.20, "mind": 0.30},
    "tara_naidhana": {"career": -0.30, "money": -0.25, "relationships": -0.25, "health": -0.40, "mind": -0.45},
    "tara_mitra": {"career": 0.25, "money": 0.20, "relationships": 0.40, "health": 0.20, "mind": 0.35},
    "tara_parama_mitra": {"career": 0.40, "money": 0.30, "relationships": 0.45, "health": 0.30, "mind": 0.35},
}
_TARA_CENTRED = _centre_rows(_TARA_RAW)

# Good-house weight vectors for Gochara; poor-house vectors are computed to give zero expectation.
# Slow planets carry larger total weight magnitudes than fast planets for both good and poor.
_GOCHARA_GOOD_RAW: dict[str, dict[str, float]] = {
    # Fast planets
    "Sun": {"career": 0.25, "money": 0.15, "relationships": 0.10, "health": 0.25, "mind": 0.15},
    "Mars": {"career": 0.30, "money": 0.20, "relationships": 0.10, "health": 0.30, "mind": 0.15},
    "Mercury": {"career": 0.20, "money": 0.20, "relationships": 0.10, "health": 0.10, "mind": 0.25},
    "Venus": {"career": 0.04, "money": 0.08, "relationships": 0.12, "health": 0.04, "mind": 0.07},
    # Slow planets
    "Jupiter": {"career": 0.55, "money": 0.60, "relationships": 0.40, "health": 0.30, "mind": 0.45},
    "Saturn": {"career": 1.15, "money": 0.90, "relationships": 0.45, "health": 0.70, "mind": 0.75},
    "Rahu": {"career": 0.75, "money": 0.65, "relationships": 0.35, "health": 0.45, "mind": 0.60},
    "Ketu": {"career": 0.80, "money": 0.65, "relationships": 0.50, "health": 0.70, "mind": 1.10},
}

WEIGHTS: dict[str, dict[str, float]] = {
    # Chandra Bala (6/12 good, 6/12 poor -> zero mean)
    "chandra_bala_good": dict(_CHANDRA_GOOD),
    "chandra_bala_poor": _neg_scaled(_CHANDRA_GOOD, len(rules.CHANDRA_BALA_GOOD_HOUSES)),

    # Tara Bala (uniform 1/9 across 9 taras -> zero mean)
    **_TARA_CENTRED,

    # Saturn standing cycles (background themes, small weights)
    "sade_sati_rising": {"career": -0.15, "money": -0.20, "relationships": -0.10, "health": -0.15, "mind": -0.20},
    "sade_sati_peak": {"career": -0.20, "money": -0.15, "relationships": -0.15, "health": -0.25, "mind": -0.30},
    "sade_sati_setting": {"career": -0.15, "money": -0.20, "relationships": -0.15, "health": -0.10, "mind": -0.15},
    "ashtama_shani": {"career": -0.25, "money": -0.15, "relationships": -0.15, "health": -0.25, "mind": -0.25},
    "kantaka_shani": {"career": -0.20, "money": -0.10, "relationships": -0.20, "health": -0.10, "mind": -0.20},

    # Dasha base theme weight (adjusted gently by natal dignity & house tone)
    "dasha_base": {"career": 0.10, "money": 0.10, "relationships": 0.10, "health": 0.10, "mind": 0.10},

    # Day quality (panchang) — weighted prominently so daily penalties outrank static fast-planet transits
    "rikta_tithi": {"career": -0.35, "money": -0.30, "relationships": -0.20, "health": -0.20, "mind": -0.30},
    "amavasya": {"career": -0.35, "money": -0.30, "relationships": -0.15, "health": -0.25, "mind": -0.35},
    "vishti_karana": {"career": -0.40, "money": -0.35, "relationships": -0.25, "health": -0.25, "mind": -0.35},
    "inauspicious_yoga": {"career": -0.35, "money": -0.25, "relationships": -0.25, "health": -0.25, "mind": -0.35},

    # Neutral informational / coming_up signals
    "neutral": {"career": 0.0, "money": 0.0, "relationships": 0.0, "health": 0.0, "mind": 0.0},
}

for _planet, _row in _GOCHARA_GOOD_RAW.items():
    _n_good = len(rules.GOCHARA_FAVOURABLE_HOUSES[_planet])
    WEIGHTS[f"gochara_{_planet.lower()}_good"] = dict(_row)
    WEIGHTS[f"gochara_{_planet.lower()}_poor"] = _neg_scaled(_row, _n_good)


def expected_saturn_cycle_drift() -> dict[str, float]:
    """Expected per-area contribution of Saturn cycle themes under uniform Saturn sign."""
    return {
        area: sum(float(WEIGHTS[k][area]) for k in SATURN_CYCLE_KEYS) / 12.0
        for area in AREAS
    }


def expected_panchang_drift() -> dict[str, float]:
    """Expected per-area contribution of panchang day-quality rules under natural frequencies."""
    return {
        area: sum(freq * float(WEIGHTS[k][area]) for k, freq in PANCHANG_FREQUENCIES.items())
        for area in AREAS
    }
