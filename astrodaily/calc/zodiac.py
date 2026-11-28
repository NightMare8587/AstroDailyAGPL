"""Signs, planets, dignities and the Navamsa (D9) division. Sign numbers are 1..12 (Aries = 1)."""

SIGNS = [
    ("Aries", "मेष"), ("Taurus", "वृषभ"), ("Gemini", "मिथुन"), ("Cancer", "कर्क"),
    ("Leo", "सिंह"), ("Virgo", "कन्या"), ("Libra", "तुला"), ("Scorpio", "वृश्चिक"),
    ("Sagittarius", "धनु"), ("Capricorn", "मकर"), ("Aquarius", "कुंभ"), ("Pisces", "मीन"),
]

# Planet keys are the Vimshottari names.
PLANET_NAMES = {
    "Sun": ("Sun", "सूर्य"), "Moon": ("Moon", "चंद्र"), "Mars": ("Mars", "मंगल"),
    "Mercury": ("Mercury", "बुध"), "Jupiter": ("Jupiter", "गुरु"), "Venus": ("Venus", "शुक्र"),
    "Saturn": ("Saturn", "शनि"), "Rahu": ("Rahu", "राहु"), "Ketu": ("Ketu", "केतु"),
}

# Ruler of each sign (index = sign number - 1).
SIGN_LORDS = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
              "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]

EXALTATION_SIGN = {"Sun": 1, "Moon": 2, "Mars": 10, "Mercury": 6, "Jupiter": 4, "Venus": 12, "Saturn": 7}
DEBILITATION_SIGN = {p: (s + 5) % 12 + 1 for p, s in EXALTATION_SIGN.items()}  # the opposite sign
OWN_SIGNS = {
    "Sun": {5}, "Moon": {4}, "Mars": {1, 8}, "Mercury": {3, 6},
    "Jupiter": {9, 12}, "Venus": {2, 7}, "Saturn": {10, 11},
}


def dignity(planet: str, sign: int) -> str | None:
    """'exalted', 'debilitated', 'own' or None. The nodes have no agreed dignities, so they get None."""
    if EXALTATION_SIGN.get(planet) == sign:
        return "exalted"
    if DEBILITATION_SIGN.get(planet) == sign:
        return "debilitated"
    if sign in OWN_SIGNS.get(planet, ()):
        return "own"
    return None


def sign_of(longitude: float) -> int:
    return int(longitude % 360.0 // 30) + 1


def navamsa_sign(longitude: float) -> int:
    """D9 sign. Each sign has nine 3 deg 20 min parts. Movable signs count from themselves,
    fixed signs from the 9th sign, dual signs from the 5th."""
    longitude %= 360.0
    sign0 = int(longitude // 30)
    part = min(int((longitude - sign0 * 30) / (30.0 / 9)), 8)
    start = (sign0 + {0: 0, 1: 8, 2: 4}[sign0 % 3]) % 12
    return (start + part) % 12 + 1


def saptamsa_sign(longitude: float) -> int:
    """D7 sign (children). Each sign has seven parts. Odd signs count from themselves, even signs from the 7th sign."""
    longitude %= 360.0
    sign0 = int(longitude // 30)
    part = min(int((longitude - sign0 * 30) / (30.0 / 7)), 6)
    start = sign0 if sign0 % 2 == 0 else (sign0 + 6) % 12
    return (start + part) % 12 + 1


def dashamsa_sign(longitude: float) -> int:
    """D10 sign (career). Each sign has ten parts of 3 degrees. Odd signs count from themselves, even signs from
    the 9th sign."""
    longitude %= 360.0
    sign0 = int(longitude // 30)
    part = min(int((longitude - sign0 * 30) / 3.0), 9)
    start = sign0 if sign0 % 2 == 0 else (sign0 + 8) % 12
    return (start + part) % 12 + 1
