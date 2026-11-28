"""Ashtakoota (Guna Milan): the traditional 36-point match from two Moon positions. Eight parts, each with its own
maximum. The rules are common published convention and have not been reviewed by a Jyotish expert.

Some parts depend on who is who (Varna, Vashya, Gana, Yoni). The first person is placed in the "groom" column of the
tables and the second in the "bride" column; swap the arguments to read it the other way round."""
from dataclasses import dataclass

from . import zodiac

NAK_SPAN = 360.0 / 27
KOOTAS = ("varna", "vashya", "tara", "yoni", "graha_maitri", "gana", "bhakoot", "nadi")
MAX = {"varna": 1, "vashya": 2, "tara": 3, "yoni": 4, "graha_maitri": 5, "gana": 6, "bhakoot": 7, "nadi": 8}  # 36

# ---- Varna (1): by Moon sign. 4 Brahmin, 3 Kshatriya, 2 Vaishya, 1 Shudra ----
_VARNA = {4: (4, 8, 12), 3: (1, 5, 9), 2: (2, 6, 10), 1: (3, 7, 11)}
VARNA_OF_SIGN = {s: v for v, signs in _VARNA.items() for s in signs}
VARNA_NAME = {4: "Brahmin", 3: "Kshatriya", 2: "Vaishya", 1: "Shudra"}

# ---- Vashya (2): the group of the Moon sign. Sagittarius and Capricorn change group halfway ----
VASHYA_GROUPS = ("Chatushpada", "Manava", "Jalachara", "Vanachara", "Keeta")
# Row: first person's group (groom), column: second person's group (bride).
_VASHYA = [
    [2.0, 1.0, 1.0, 0.0, 1.0],
    [1.0, 2.0, 1.5, 0.0, 1.0],
    [1.0, 1.5, 2.0, 0.0, 1.0],
    [1.5, 0.0, 1.0, 2.0, 0.0],
    [1.0, 1.0, 1.0, 0.0, 2.0],
]


def vashya_group(moon_longitude: float) -> str:
    sign = zodiac.sign_of(moon_longitude)
    first_half = (moon_longitude % 30.0) < 15.0
    if sign in (1, 2):
        return "Chatushpada"
    if sign in (3, 6, 7, 11):
        return "Manava"
    if sign in (4, 12):
        return "Jalachara"
    if sign == 5:
        return "Vanachara"
    if sign == 8:
        return "Keeta"
    if sign == 9:
        return "Manava" if first_half else "Chatushpada"
    return "Chatushpada" if first_half else "Jalachara"  # Capricorn


# ---- Yoni (4): the animal of the birth star ----
YONI_OF_NAKSHATRA = (
    "Horse", "Elephant", "Sheep", "Serpent", "Serpent", "Dog", "Cat", "Sheep", "Cat",
    "Rat", "Rat", "Cow", "Buffalo", "Tiger", "Buffalo", "Tiger", "Deer", "Deer",
    "Dog", "Monkey", "Mongoose", "Monkey", "Lion", "Horse", "Lion", "Cow", "Elephant",
)
YONI_ANIMALS = ("Horse", "Elephant", "Sheep", "Serpent", "Dog", "Cat", "Rat", "Cow", "Buffalo", "Tiger", "Deer",
                "Monkey", "Mongoose", "Lion")
# Same animal 4, natural enemies 0 (Horse-Buffalo, Elephant-Lion, Sheep-Monkey, Serpent-Mongoose, Dog-Deer, Cat-Rat,
# Cow-Tiger). Rows and columns follow YONI_ANIMALS.
_YONI_MATRIX = [
    [4, 2, 2, 3, 2, 2, 2, 1, 0, 1, 1, 3, 2, 1],
    [2, 4, 3, 3, 2, 2, 2, 2, 3, 1, 2, 3, 2, 0],
    [2, 3, 4, 2, 1, 2, 1, 3, 3, 1, 2, 0, 3, 1],
    [3, 3, 2, 4, 2, 1, 1, 1, 1, 2, 2, 2, 0, 2],
    [2, 2, 1, 2, 4, 2, 1, 2, 2, 1, 0, 2, 1, 1],
    [2, 2, 2, 1, 2, 4, 0, 2, 2, 1, 3, 3, 2, 1],
    [2, 2, 1, 1, 1, 0, 4, 2, 2, 2, 2, 2, 1, 2],
    [1, 2, 3, 1, 2, 2, 2, 4, 3, 0, 3, 2, 2, 1],
    [0, 3, 3, 1, 2, 2, 2, 3, 4, 1, 2, 2, 2, 1],
    [1, 1, 1, 2, 1, 1, 2, 0, 1, 4, 1, 1, 2, 1],
    [1, 2, 2, 2, 0, 3, 2, 3, 2, 1, 4, 2, 2, 1],
    [3, 3, 0, 2, 2, 3, 2, 2, 2, 1, 2, 4, 3, 2],
    [2, 2, 3, 0, 1, 2, 1, 2, 2, 2, 2, 3, 4, 2],
    [1, 0, 1, 2, 1, 1, 2, 1, 1, 1, 1, 2, 2, 4],
]

# ---- Gana (6): the temperament of the birth star ----
GANA_OF_NAKSHATRA = (
    "Deva", "Manushya", "Rakshasa", "Manushya", "Deva", "Manushya", "Deva", "Deva", "Rakshasa",
    "Rakshasa", "Manushya", "Manushya", "Deva", "Rakshasa", "Deva", "Rakshasa", "Deva", "Rakshasa",
    "Rakshasa", "Manushya", "Manushya", "Deva", "Rakshasa", "Rakshasa", "Manushya", "Manushya", "Deva",
)
GANAS = ("Deva", "Manushya", "Rakshasa")
_GANA = {("Deva", "Deva"): 6, ("Deva", "Manushya"): 5, ("Deva", "Rakshasa"): 1,
         ("Manushya", "Deva"): 6, ("Manushya", "Manushya"): 6, ("Manushya", "Rakshasa"): 0,
         ("Rakshasa", "Deva"): 0, ("Rakshasa", "Manushya"): 0, ("Rakshasa", "Rakshasa"): 6}

# ---- Nadi (8): the channel of the birth star. Two people in the same one score 0 ----
NADI_OF_NAKSHATRA = tuple(("Aadi", "Madhya", "Antya")[n] for n in
                          [0, 1, 2, 2, 1, 0, 0, 1, 2, 2, 1, 0, 0, 1, 2, 2, 1, 0, 0, 1, 2, 2, 1, 0, 0, 1, 2])

# ---- Graha Maitri (5): how the two Moon-sign lords get on ----
_FRIENDS = {
    "Sun": {"Moon", "Mars", "Jupiter"}, "Moon": {"Sun", "Mercury"}, "Mars": {"Sun", "Moon", "Jupiter"},
    "Mercury": {"Sun", "Venus"}, "Jupiter": {"Sun", "Moon", "Mars"}, "Venus": {"Mercury", "Saturn"},
    "Saturn": {"Mercury", "Venus"},
}
_ENEMIES = {
    "Sun": {"Venus", "Saturn"}, "Moon": set(), "Mars": {"Mercury"}, "Mercury": {"Moon"},
    "Jupiter": {"Mercury", "Venus"}, "Venus": {"Sun", "Moon"}, "Saturn": {"Sun", "Moon", "Mars"},
}


def _regard(a: str, b: str) -> str:
    return "F" if b in _FRIENDS[a] else "E" if b in _ENEMIES[a] else "N"


def graha_maitri_points(lord1: str, lord2: str) -> float:
    if lord1 == lord2:
        return 5.0
    pair = "".join(sorted(_regard(lord1, lord2) + _regard(lord2, lord1)))
    return {"FF": 5.0, "FN": 4.0, "NN": 3.0, "EF": 1.0, "EN": 0.5, "EE": 0.0}[pair]


def tara_points(nak1: int, nak2: int) -> float:
    """Count each birth star from the other; a remainder of 3, 5 or 7 (counting in nines) is the difficult one."""
    def bad(a: int, b: int) -> bool:
        return ((b - a) % 27 + 1) % 9 in (3, 5, 7)
    n = (0 if bad(nak1, nak2) else 1) + (0 if bad(nak2, nak1) else 1)
    return {2: 3.0, 1: 1.5, 0: 0.0}[n]


def bhakoot_points(sign1: int, sign2: int) -> float:
    d = (sign2 - sign1) % 12 + 1  # counting the second sign from the first
    return 0.0 if d in (2, 12, 5, 9, 6, 8) else 7.0


@dataclass(frozen=True)
class Moon:
    """What the match needs about a person: where the Moon is."""
    longitude: float

    @property
    def sign(self) -> int:
        return zodiac.sign_of(self.longitude)

    @property
    def nakshatra(self) -> int:
        return int(self.longitude % 360.0 // NAK_SPAN) + 1

    @property
    def lord(self) -> str:
        return zodiac.SIGN_LORDS[self.sign - 1]


def match(a: Moon, b: Moon) -> dict:
    """The eight parts for [a] (first column) and [b] (second column), and the total out of 36."""
    va, vb = vashya_group(a.longitude), vashya_group(b.longitude)
    ya, yb = YONI_OF_NAKSHATRA[a.nakshatra - 1], YONI_OF_NAKSHATRA[b.nakshatra - 1]
    ga, gb = GANA_OF_NAKSHATRA[a.nakshatra - 1], GANA_OF_NAKSHATRA[b.nakshatra - 1]
    na, nb = NADI_OF_NAKSHATRA[a.nakshatra - 1], NADI_OF_NAKSHATRA[b.nakshatra - 1]
    points = {
        "varna": 1.0 if VARNA_OF_SIGN[a.sign] >= VARNA_OF_SIGN[b.sign] else 0.0,
        "vashya": _VASHYA[VASHYA_GROUPS.index(va)][VASHYA_GROUPS.index(vb)],
        "tara": tara_points(a.nakshatra, b.nakshatra),
        "yoni": float(_YONI_MATRIX[YONI_ANIMALS.index(ya)][YONI_ANIMALS.index(yb)]),
        "graha_maitri": graha_maitri_points(a.lord, b.lord),
        "gana": float(_GANA[(ga, gb)]),
        "bhakoot": bhakoot_points(a.sign, b.sign),
        "nadi": 0.0 if na == nb else 8.0,
    }
    detail = {
        "varna": (VARNA_NAME[VARNA_OF_SIGN[a.sign]], VARNA_NAME[VARNA_OF_SIGN[b.sign]]),
        "vashya": (va, vb), "tara": (a.nakshatra, b.nakshatra), "yoni": (ya, yb),
        "graha_maitri": (a.lord, b.lord), "gana": (ga, gb), "bhakoot": (a.sign, b.sign), "nadi": (na, nb),
    }
    return {"parts": [{"key": k, "points": points[k], "max": MAX[k], "a": detail[k][0], "b": detail[k][1]}
                      for k in KOOTAS],
            "total": sum(points.values()), "max": 36}
