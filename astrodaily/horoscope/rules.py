"""Classical Jyotish rule tables for daily horoscope signals.

ALL RULE TABLES IN THIS FILE ARE UNVERIFIED until checked against public-domain Sanskrit
sources (Brihat Parashara Hora Shastra, Phaladeepika, Brihat Samhita).
"""

RULESET_VERSION = "0.2-unverified"

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

# UNVERIFIED: Traditional weekday rulers (Sunday-first) and activity tags.
VARA_LORDS: dict[str, str] = {
    "Sunday": "Sun",
    "Monday": "Moon",
    "Tuesday": "Mars",
    "Wednesday": "Mercury",
    "Thursday": "Jupiter",
    "Friday": "Venus",
    "Saturday": "Saturn",
}

VARA_SUITS: dict[str, tuple[str, ...]] = {
    "Sunday": ("authority", "health", "government_matters"),
    "Monday": ("travel", "creativity", "caring_for_others"),
    "Tuesday": ("courage", "property", "avoid_conflict"),
    "Wednesday": ("trade", "learning", "communication"),
    "Thursday": ("teaching", "finance", "auspicious_starts"),
    "Friday": ("arts", "relationships", "comfort"),
    "Saturday": ("discipline", "service", "long_term_work"),
}

# UNVERIFIED: Classical muhurta nakshatra categories partitioning 1..27.
# category_slug -> (display_name, kind, nakshatra_numbers, suits)
NAKSHATRA_CATEGORIES: dict[str, tuple[str, str, frozenset[int], tuple[str, ...]]] = {
    "dhruva": (
        "Dhruva",
        "favourable",
        frozenset({4, 12, 21, 26}),
        ("foundations", "long_term_commitments", "planting"),
    ),
    "chara": (
        "Chara",
        "favourable",
        frozenset({7, 15, 22, 23, 24}),
        ("travel", "vehicles", "movement"),
    ),
    "kshipra": (
        "Kshipra",
        "favourable",
        frozenset({1, 8, 13}),
        ("trade", "learning", "fresh_starts"),
    ),
    "mridu": (
        "Mridu",
        "favourable",
        frozenset({5, 14, 17, 27}),
        ("arts", "friendships", "gentle_work"),
    ),
    "ugra": (
        "Ugra",
        "unfavourable",
        frozenset({2, 10, 11, 20, 25}),
        ("decisive_tasks", "avoid_auspicious_starts"),
    ),
    "tikshna": (
        "Tikshna",
        "unfavourable",
        frozenset({6, 9, 18, 19}),
        ("investigation", "repair", "avoid_new_ventures"),
    ),
    "mishra": (
        "Mishra",
        "info",
        frozenset({3, 16}),
        ("mixed_routine", "discipline"),
    ),
}

NAKSHATRA_CATEGORY_BY_NUM: dict[int, str] = {
    num: slug
    for slug, (_, _, nums, _) in NAKSHATRA_CATEGORIES.items()
    for num in nums
}

# UNVERIFIED: Classical 5-fold tithi groups within a paksha (plus Amavasya = 30).
# signal_id -> (display_name, kind, paksha_numbers, suits)
# Nanda, Bhadra, Jaya, Purna are treated as mild favourable per muhurta tradition.
TITHI_CATEGORIES: dict[str, tuple[str, str, frozenset[int], tuple[str, ...]]] = {
    "tithi_nanda": ("Nanda", "favourable", frozenset({1, 6, 11}), ("celebrations", "joyful_beginnings")),
    "tithi_bhadra": ("Bhadra", "favourable", frozenset({2, 7, 12}), ("health", "auspicious_acts")),
    "tithi_jaya": ("Jaya", "favourable", frozenset({3, 8, 13}), ("competition", "victory")),
    "rikta_tithi": ("Rikta", "unfavourable", frozenset({4, 9, 14}), ("completing_pending_work", "avoid_launches")),
    "tithi_purna": ("Purna", "favourable", frozenset({5, 10, 15}), ("completion", "journeys")),
}

TITHI_SIGNAL_BY_PAKSHA_NUM: dict[int, str] = {
    n: sig_id
    for sig_id, (_, _, nums, _) in TITHI_CATEGORIES.items()
    for n in nums
}

# UNVERIFIED: Special lunar-day informational signals (tithi 1..30 -> (signal_id, label, reason)).
SPECIAL_TITHI_DAYS: dict[int, tuple[str, str, str]] = {
    11: ("special_ekadashi", "Ekadashi", "Shukla Ekadashi is traditionally observed for mindful simplicity."),
    26: ("special_ekadashi", "Ekadashi", "Krishna Ekadashi is traditionally observed for mindful simplicity."),
    13: ("special_pradosh", "Pradosh", "Shukla Pradosh (Trayodashi) favours calm evening reflection."),
    28: ("special_pradosh", "Pradosh", "Krishna Pradosh (Trayodashi) favours calm evening reflection."),
    19: ("special_sankashti", "Sankashti Chaturthi", "Sankashti Chaturthi is traditionally kept for steady resolve."),
    15: ("special_purnima", "Purnima", "Purnima marks full-moon culmination and sharing."),
}

# UNVERIFIED: Bounded natal-lord tone modifiers for running dasha themes.
DASHA_DIGNITY_TONE: dict[str | None, float] = {
    "exalted": 0.20,
    "own": 0.10,
    "debilitated": -0.20,
    None: 0.0,
}

# UNVERIFIED: Centred natal-house tone modifiers across houses 1..12 (sum == 0.0).
_RAW_DASHA_HOUSE_TONE: dict[int, float] = {
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
_DASHA_HOUSE_MEAN = sum(_RAW_DASHA_HOUSE_TONE.values()) / 12.0
DASHA_HOUSE_TONE: dict[int, float] = {
    h: v - _DASHA_HOUSE_MEAN for h, v in _RAW_DASHA_HOUSE_TONE.items()
}
