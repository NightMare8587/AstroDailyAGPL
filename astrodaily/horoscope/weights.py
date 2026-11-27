"""Tunable weights and scoring thresholds for the daily horoscope engine.

Kept as pure Python data so weights and scoring bands can be tuned (or monkeypatched in tests)
without changing rule or scoring logic. All area weights stay in [-2.0, 2.0].

Centring method:
- Symmetric/partition rule families (Chandra Bala, every Gochara planet, Tara Bala, the 27-nakshatra
  category partition, and the 30-tithi category partition) have their per-signal weights centred
  in this module so each family's expected contribution per area under a uniform distribution is 0.0.
- Dasha themes use ``dasha_base = 0.0`` across all areas plus bounded natal dignity and
  zero-mean house tone from ``rules``.
- One-sided rule families that only emit negative signals (Saturn standing cycles in 5/12 houses;
  Vishti karana at 8/60 and inauspicious yogas at 7/27) expose ``expected_saturn_cycle_drift()``
  and ``expected_panchang_drift()`` computed directly from ``WEIGHTS`` and ``rules``. ``area_scores``
  subtracts those drifts when those rule families were evaluated.
"""
from . import rules

AREAS: list[str] = ["career", "money", "relationships", "health", "mind"]

SCORING_VERSION = "0.3"

# Sum of weights per area is clipped to AREA_CLIP before mapping to 1..5 via AREA_THRESHOLDS.
AREA_CLIP: tuple[float, float] = (-4.0, 4.0)
# Symmetric thresholds around 0.0:
# score 1 if s < -t1, 2 if -t1 <= s < -t0, 3 if -t0 <= s <= t0, 4 if t0 < s <= t1, 5 if s > t1.
AREA_THRESHOLDS: tuple[float, float, float, float] = (-2.3, -0.78, 0.78, 2.3)

# Natural frequencies used to compute expected drift of one-sided rules from the rule tables.
SATURN_CYCLE_KEYS: tuple[str, ...] = (
    "sade_sati_rising",
    "sade_sati_peak",
    "sade_sati_setting",
    "ashtama_shani",
    "ardhashtama_shani",
)
PANCHANG_FREQUENCIES: dict[str, float] = {
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

# Nakshatra category weights (27 nakshatras: 16 favourable, 9 unfavourable, 2 info at 0.0).
_NAK_FAV_RAW: dict[str, dict[str, float]] = {
    "nakshatra_dhruva": {"career": 0.30, "money": 0.25, "relationships": 0.25, "health": 0.20, "mind": 0.20},
    "nakshatra_chara": {"career": 0.25, "money": 0.20, "relationships": 0.20, "health": 0.25, "mind": 0.25},
    "nakshatra_kshipra": {"career": 0.30, "money": 0.30, "relationships": 0.15, "health": 0.20, "mind": 0.25},
    "nakshatra_mridu": {"career": 0.15, "money": 0.15, "relationships": 0.35, "health": 0.20, "mind": 0.30},
}
_NAK_POS_TOTAL = {
    area: sum(
        len(rules.NAKSHATRA_CATEGORIES[slug.removeprefix("nakshatra_")][2]) * row[area]
        for slug, row in _NAK_FAV_RAW.items()
    )
    for area in AREAS
}
# Split negative mass across Ugra (5) and Tikshna (4) so 5*ugra + 4*tikshna == -_NAK_POS_TOTAL.
_NAK_UGRA_COUNT = len(rules.NAKSHATRA_CATEGORIES["ugra"][2])
_NAK_TIKSHNA_COUNT = len(rules.NAKSHATRA_CATEGORIES["tikshna"][2])
_NAK_NEG_TOTAL_COUNT = _NAK_UGRA_COUNT + _NAK_TIKSHNA_COUNT
_NAK_UGRA = {area: -_NAK_POS_TOTAL[area] / _NAK_NEG_TOTAL_COUNT for area in AREAS}
_NAK_TIKSHNA = {
    area: (-_NAK_POS_TOTAL[area] - _NAK_UGRA_COUNT * _NAK_UGRA[area]) / _NAK_TIKSHNA_COUNT
    for area in AREAS
}

# Tithi category weights (30 tithis: 6 Nanda, 6 Bhadra, 6 Jaya, 5 Purna, 6 Rikta, 1 Amavasya).
_TITHI_FAV_RAW: dict[str, dict[str, float]] = {
    "tithi_nanda": {"career": 0.20, "money": 0.20, "relationships": 0.30, "health": 0.20, "mind": 0.25},
    "tithi_bhadra": {"career": 0.25, "money": 0.20, "relationships": 0.20, "health": 0.30, "mind": 0.20},
    "tithi_jaya": {"career": 0.30, "money": 0.25, "relationships": 0.15, "health": 0.25, "mind": 0.20},
    "tithi_purna": {"career": 0.25, "money": 0.25, "relationships": 0.25, "health": 0.20, "mind": 0.25},
}
# Count of each tithi category across 1..30 (tithi 30 is Amavasya, so Purna has 5).
_TITHI_POS_COUNTS = {"tithi_nanda": 6, "tithi_bhadra": 6, "tithi_jaya": 6, "tithi_purna": 5}
_TITHI_POS_TOTAL = {
    area: sum(_TITHI_POS_COUNTS[k] * row[area] for k, row in _TITHI_FAV_RAW.items())
    for area in AREAS
}
# Make Amavasya slightly stronger than Rikta while keeping 6*rikta + 1*amavasya == -_TITHI_POS_TOTAL.
_TITHI_RIKTA = {area: -_TITHI_POS_TOTAL[area] / 7.25 for area in AREAS}
_TITHI_AMAVASYA = {area: -1.25 * _TITHI_POS_TOTAL[area] / 7.25 for area in AREAS}

# Good-house weight vectors for Gochara; poor-house vectors are computed to give zero expectation.
# Slow planets carry larger total weight magnitudes than fast planets for both good and poor.
_GOCHARA_GOOD_RAW: dict[str, dict[str, float]] = {
    # Fast planets (smaller than daily nakshatra/tithi so daily lunar rhythm drives card variety)
    "Sun": {"career": 0.22, "money": 0.14, "relationships": 0.08, "health": 0.22, "mind": 0.14},
    "Mars": {"career": 0.25, "money": 0.18, "relationships": 0.08, "health": 0.25, "mind": 0.14},
    "Mercury": {"career": 0.18, "money": 0.18, "relationships": 0.08, "health": 0.08, "mind": 0.22},
    "Venus": {"career": 0.04, "money": 0.07, "relationships": 0.10, "health": 0.04, "mind": 0.06},
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

    # Nakshatra categories (27 nakshatras -> zero mean)
    **{k: dict(v) for k, v in _NAK_FAV_RAW.items()},
    "nakshatra_ugra": _NAK_UGRA,
    "nakshatra_tikshna": _NAK_TIKSHNA,
    "nakshatra_mishra": {"career": 0.0, "money": 0.0, "relationships": 0.0, "health": 0.0, "mind": 0.0},

    # Tithi categories (30 tithis -> zero mean)
    **{k: dict(v) for k, v in _TITHI_FAV_RAW.items()},
    "rikta_tithi": _TITHI_RIKTA,
    "amavasya": _TITHI_AMAVASYA,

    # Saturn standing cycles (background themes, small weights)
    "sade_sati_rising": {"career": -0.15, "money": -0.20, "relationships": -0.10, "health": -0.15, "mind": -0.20},
    "sade_sati_peak": {"career": -0.20, "money": -0.15, "relationships": -0.15, "health": -0.25, "mind": -0.30},
    "sade_sati_setting": {"career": -0.15, "money": -0.20, "relationships": -0.15, "health": -0.10, "mind": -0.15},
    "ashtama_shani": {"career": -0.25, "money": -0.15, "relationships": -0.15, "health": -0.25, "mind": -0.25},
    "ardhashtama_shani": {"career": -0.20, "money": -0.10, "relationships": -0.20, "health": -0.10, "mind": -0.20},

    # Dasha base is zero so Level B centres around 3.0; only bounded dignity + centred house tone shift it.
    "dasha_base": {"career": 0.0, "money": 0.0, "relationships": 0.0, "health": 0.0, "mind": 0.0},

    # One-sided panchang penalties
    "vishti_karana": {"career": -0.35, "money": -0.30, "relationships": -0.25, "health": -0.20, "mind": -0.30},
    "inauspicious_yoga": {"career": -0.35, "money": -0.25, "relationships": -0.25, "health": -0.25, "mind": -0.30},

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
    """Expected per-area contribution of one-sided panchang penalties (Vishti, inauspicious yogas)."""
    return {
        area: sum(freq * float(WEIGHTS[k][area]) for k, freq in PANCHANG_FREQUENCIES.items())
        for area in AREAS
    }
