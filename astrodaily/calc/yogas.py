"""Simple, widely used chart readings built from a computed chart: how strong each planet sits, which houses it aspects,
and a short list of yogas and doshas. Common convention, not verified by a Jyotish expert (see docs/chart-readings.md).
Houses are whole-sign houses counted from the Lagna."""
from datetime import datetime

from . import ephem, zodiac
from .matching import _ENEMIES, _FRIENDS

KENDRA = (1, 4, 7, 10)
TRIKONA = (5, 9)
DUSTHANA = (6, 8, 12)

# How close to the Sun a planet is "combust" (its light lost in the Sun's glare), in degrees.
COMBUST_ORB = {"Moon": 12.0, "Mars": 17.0, "Mercury": 14.0, "Jupiter": 11.0, "Venus": 10.0, "Saturn": 15.0}

# The houses a planet looks at, counted from where it stands (the 7th for all, plus these). The nodes use the 5th and 9th.
EXTRA_ASPECTS = {"Mars": (4, 8), "Jupiter": (5, 9), "Saturn": (3, 10), "Rahu": (5, 9), "Ketu": (5, 9)}

PANCHA_MAHAPURUSHA = {"Mars": "ruchaka", "Mercury": "bhadra", "Jupiter": "hamsa", "Venus": "malavya", "Saturn": "shasha"}


def _angle(a: float, b: float) -> float:
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


def strength(planet: dict, sun_longitude: float) -> dict:
    """A simple strength guide: points for the sign it is in (exalted, own, a friend's, an enemy's, debilitated) and for the
    house (kendra or trikona up, 6th, 8th and 12th down), less one when combust. 'strong' 3+, 'steady' 0 to 2, 'tender'
    below 0. The nodes have no sign rules, so only their house counts."""
    key, pts = planet["key"], 0
    if key not in ("Rahu", "Ketu"):
        dignity = planet["dignity"]
        if dignity == "exalted":
            pts += 3
        elif dignity == "own":
            pts += 2
        elif dignity == "debilitated":
            pts -= 3
        else:
            lord = zodiac.SIGN_LORDS[planet["sign"] - 1]
            if lord in _FRIENDS[key]:
                pts += 1
            elif lord in _ENEMIES[key]:
                pts -= 1
    h = planet["house"]
    pts += 1 if h in KENDRA or h in TRIKONA else -1 if h in DUSTHANA else 0
    if key in COMBUST_ORB and _angle(planet["longitude"], sun_longitude) < COMBUST_ORB[key]:
        pts -= 1
    level = "strong" if pts >= 3 else "steady" if pts >= 0 else "tender"
    return {"score": pts, "level": level}


def aspects(planet: dict, by_house: dict[int, list[str]]) -> dict:
    """The houses a planet looks at and the planets in them."""
    h = planet["house"]
    houses = sorted({(h + n - 2) % 12 + 1 for n in (7, *EXTRA_ASPECTS.get(planet["key"], ()))})
    return {"houses": houses, "planets": [k for x in houses for k in by_house.get(x, []) if k != planet["key"]]}


def _between_nodes(rahu: float, ketu: float, lon: float) -> bool:
    """Whether [lon] is on the arc running from Rahu round to Ketu."""
    return (lon - rahu) % 360.0 < (ketu - rahu) % 360.0


def detect(chart: dict, moment: datetime) -> list[dict]:
    """The yogas and doshas that are present: [{key, kind, planets}]. kind is 'yoga', 'dosha' or 'phase' (Sade Sati)."""
    p = {x["key"]: x for x in chart["planets"]}
    found: list[dict] = []

    def add(key: str, kind: str, planets: list[str]) -> None:
        found.append({"key": key, "kind": kind, "planets": planets})

    if p["Mars"]["house"] in (1, 2, 4, 7, 8, 12):
        add("mangal_dosha", "dosha", ["Mars"])
    seven = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
    r, k = p["Rahu"]["longitude"], p["Ketu"]["longitude"]
    sides = {_between_nodes(r, k, p[x]["longitude"]) for x in seven}
    if len(sides) == 1:
        add("kaal_sarp", "dosha", ["Rahu", "Ketu"])
    if (p["Jupiter"]["sign"] - p["Moon"]["sign"]) % 12 + 1 in KENDRA:
        add("gajakesari", "yoga", ["Jupiter", "Moon"])
    if p["Sun"]["sign"] == p["Mercury"]["sign"]:
        add("budhaditya", "yoga", ["Sun", "Mercury"])
    if p["Moon"]["sign"] == p["Mars"]["sign"]:
        add("chandra_mangal", "yoga", ["Moon", "Mars"])
    for planet, key in PANCHA_MAHAPURUSHA.items():
        if p[planet]["dignity"] in ("own", "exalted") and p[planet]["house"] in KENDRA:
            add(key, "yoga", [planet])
    # Sade Sati: Saturn, as it moves now, in the sign before, on, or after the natal Moon sign.
    saturn_now = zodiac.sign_of(ephem.body_position(ephem.datetime_to_jd(moment), ephem.SATURN)[0])
    if (saturn_now - p["Moon"]["sign"]) % 12 in (0, 1, 11):
        add("sade_sati", "phase", ["Saturn", "Moon"])
    return found
