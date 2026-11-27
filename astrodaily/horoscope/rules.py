"""Classical Jyotish rule tables for daily horoscope signals.

ALL RULE TABLES IN THIS FILE ARE UNVERIFIED until checked against public-domain Sanskrit
sources (Brihat Parashara Hora Shastra, Phaladeepika, Brihat Samhita).
"""

RULESET_VERSION = "0.1-unverified"

# UNVERIFIED: houses from natal Moon where transiting Moon is favourable (Chandra Bala).
CHANDRA_BALA_GOOD_HOUSES: frozenset[int] = frozenset({1, 3, 6, 7, 10, 11})

# UNVERIFIED: 9-part Tara Bala cycle from birth nakshatra to today's nakshatra (inclusive).
# (slug, display_name, signal_kind)
TARA_TABLE: dict[int, tuple[str, str, str]] = {
    1: ("janma", "Janma", "unfavourable"),           # mixed / small caution
    2: ("sampat", "Sampat", "favourable"),
    3: ("vipat", "Vipat", "unfavourable"),
    4: ("kshema", "Kshema", "favourable"),
    5: ("pratyak", "Pratyak", "unfavourable"),
    6: ("sadhana", "Sadhana", "favourable"),
    7: ("naidhana", "Naidhana", "unfavourable"),
    8: ("mitra", "Mitra", "favourable"),
    9: ("parama_mitra", "Parama Mitra", "favourable"),
}

# UNVERIFIED: Gochara favourable houses counted from the natal Moon sign.
# Note: Rahu and Ketu rows are especially uncertain across Jyotish texts.
GOCHARA_FAVOURABLE_HOUSES: dict[str, frozenset[int]] = {
    "Sun": frozenset({3, 6, 10, 11}),
    "Moon": frozenset({1, 3, 6, 7, 10, 11}),
    "Mars": frozenset({3, 6, 11}),
    "Mercury": frozenset({2, 4, 6, 8, 10, 11}),
    "Jupiter": frozenset({2, 5, 7, 9, 11}),
    "Venus": frozenset({1, 2, 3, 4, 5, 8, 9, 11, 12}),
    "Saturn": frozenset({3, 6, 11}),
    "Rahu": frozenset({3, 6, 10, 11}),   # UNVERIFIED — especially uncertain
    "Ketu": frozenset({3, 6, 11}),       # UNVERIFIED — especially uncertain
}

SLOW_GRAHAS: frozenset[str] = frozenset({"Saturn", "Jupiter", "Rahu", "Ketu"})
COMING_UP_GRAHAS: tuple[str, ...] = ("Saturn", "Jupiter", "Rahu", "Ketu")
COMING_UP_WINDOW_DAYS: float = 30.0

# UNVERIFIED: Rikta tithi numbers within each paksha (Chaturthi=4, Navami=9, Chaturdashi=14).
RIKTA_PAKSHA_TITHIS: frozenset[int] = frozenset({4, 9, 14})
AMAVASYA_TITHI_NUMBER: int = 30
VISHTI_KARANA_EN: str = "Vishti (Bhadra)"

# UNVERIFIED: Nitya yogas conventionally treated as challenging for new beginnings.
INAUSPICIOUS_YOGAS: frozenset[str] = frozenset({
    "Vyatipata",
    "Vaidhriti",
    "Atiganda",
    "Shula",
    "Ganda",
    "Vyaghata",
    "Parigha",
})

# UNVERIFIED: Traditional weekday rulers (Sunday-first).
VARA_LORDS: dict[str, str] = {
    "Sunday": "Sun",
    "Monday": "Moon",
    "Tuesday": "Mars",
    "Wednesday": "Mercury",
    "Thursday": "Jupiter",
    "Friday": "Venus",
    "Saturday": "Saturn",
}

# UNVERIFIED: Bounded natal-lord tone modifiers for running dasha themes.
DASHA_DIGNITY_TONE: dict[str | None, float] = {
    "exalted": 0.25,
    "own": 0.15,
    "debilitated": -0.25,
    None: 0.0,
}

# UNVERIFIED: Bounded natal-house tone modifiers for running dasha lords (whole-sign from lagna).
DASHA_HOUSE_TONE: dict[int, float] = {
    1: 0.15,
    2: 0.05,
    3: 0.0,
    4: 0.10,
    5: 0.15,
    6: -0.15,
    7: 0.10,
    8: -0.20,
    9: 0.20,
    10: 0.15,
    11: 0.15,
    12: -0.15,
}
