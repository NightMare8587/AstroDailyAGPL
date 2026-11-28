import re
from datetime import datetime, timezone

import pytest

from astrodaily.calc import yogas as y
from astrodaily.calc import zodiac
from astrodaily.content import yoga_text
from astrodaily.content.lint import BANNED_EN, BANNED_HI

NOW = datetime(2026, 11, 28, 12, 0, tzinfo=timezone.utc)


def planet(key, sign, house, longitude=None, dignity=None, lon_in=10.0, retro=False):
    return {"key": key, "sign": sign, "house": house, "longitude": longitude if longitude is not None else (sign - 1) * 30 + lon_in,
            "dignity": dignity, "retrograde": retro, "degree_in_sign": lon_in}


def chart(**over):
    """A quiet chart: nothing in a special place."""
    base = {"Sun": (1, 1), "Moon": (2, 2), "Mars": (3, 3), "Mercury": (6, 6), "Jupiter": (9, 9), "Venus": (11, 11),
            "Saturn": (10, 10), "Rahu": (5, 5), "Ketu": (11, 11)}
    base.update(over)
    return {"planets": [planet(k, s, h) for k, (s, h) in base.items()], "lagna": {"sign": 1}}


def keys(c):
    return {f["key"] for f in y.detect(c, NOW)}


# ---- strength ----

def test_strength_points_for_sign_and_house():
    assert y.strength(planet("Jupiter", 4, 4, dignity="exalted"), 200.0) == {"score": 4, "level": "strong"}  # +3, kendra +1
    assert y.strength(planet("Mars", 1, 1, dignity="own"), 200.0)["score"] == 3
    assert y.strength(planet("Saturn", 1, 8, dignity="debilitated"), 200.0) == {"score": -4, "level": "tender"}
    # a friend's sign (+1) in the 6th (-1)
    assert y.strength(planet("Mars", 5, 6), 200.0)["score"] == 0  # Mars in Leo (the Sun's sign: a friend)
    assert y.strength(planet("Mars", 3, 6), 200.0)["score"] == -2  # Mercury's sign: an enemy (-1), 6th house (-1)
    assert y.strength(planet("Rahu", 3, 5), 200.0) == {"score": 1, "level": "steady"}  # the nodes: the house only


def test_a_planet_close_to_the_sun_is_combust():
    near = planet("Mercury", 1, 1, longitude=15.0)
    far = planet("Mercury", 1, 1, longitude=15.0)
    assert y.strength(near, 20.0)["score"] == y.strength(far, 100.0)["score"] - 1
    assert y.strength(planet("Sun", 1, 1, longitude=15.0), 15.0)["score"] >= 0  # the Sun is never combust


# ---- aspects ----

def test_every_planet_looks_at_the_seventh_and_some_look_at_more():
    by_house = {1: ["Sun"], 4: ["Mars"], 7: ["Moon"], 8: ["Venus"], 10: ["Jupiter"]}
    sun = y.aspects(planet("Sun", 1, 1), by_house)
    assert sun == {"houses": [7], "planets": ["Moon"]}
    mars = y.aspects(planet("Mars", 4, 4), by_house)
    assert mars["houses"] == [7, 10, 11] and mars["planets"] == ["Moon", "Jupiter"]  # the 4th, 7th and 8th from house 4
    jup = y.aspects(planet("Jupiter", 10, 10), by_house)
    assert jup["houses"] == [2, 4, 6] and jup["planets"] == ["Mars"]  # the 5th, 7th and 9th from house 10
    sat = y.aspects(planet("Saturn", 12, 12), {})
    assert sat["houses"] == [2, 6, 9]  # the 3rd, 7th and 10th from house 12


# ---- yogas and doshas ----

def test_a_quiet_chart_has_none_of_the_yogas():
    found = keys(chart())
    assert not found & {"mangal_dosha", "kaal_sarp", "gajakesari", "budhaditya", "chandra_mangal", "ruchaka", "bhadra", "hamsa",
                        "malavya", "shasha"}


def test_mangal_dosha_is_mars_in_1_4_7_8_or_12():
    # Brihat Parashara Hora Shastra 80.47. The 2nd house is not in this verse (other texts add it; see docs/mangal-dosha-sources.md).
    for h in (1, 4, 7, 8, 12):
        near = h % 12 + 1  # Jupiter and Venus one house on from Mars, where they neither join nor look at it
        assert "mangal_dosha" in keys(chart(Mars=(h, h), Jupiter=(near, near), Venus=(near, near))), h
    for h in (2, 3, 5, 6, 9, 10, 11):
        assert "mangal_dosha" not in keys(chart(Mars=(h, h))), h


def test_mangal_dosha_is_not_present_when_jupiter_or_venus_joins_or_aspects_mars():
    assert "mangal_dosha" in keys(chart(Mars=(7, 7)))
    assert "mangal_dosha" not in keys(chart(Mars=(7, 7), Jupiter=(7, 7)))   # Jupiter with Mars
    assert "mangal_dosha" not in keys(chart(Mars=(7, 7), Venus=(7, 7)))     # Venus with Mars
    assert "mangal_dosha" not in keys(chart(Mars=(7, 7), Jupiter=(3, 3)))   # Jupiter's 5th aspect from house 3 reaches house 7
    assert "mangal_dosha" not in keys(chart(Mars=(7, 7), Venus=(1, 1)))     # Venus looks at the 7th from house 1
    assert "mangal_dosha" in keys(chart(Mars=(7, 7), Jupiter=(4, 4)))       # house 4 does not look at house 7
    assert "mangal_dosha" in keys(chart(Mars=(7, 7), Saturn=(7, 7), Mercury=(7, 7)))  # other planets do not count


def test_gajakesari_is_jupiter_in_a_pillar_house_from_the_moon():
    assert "gajakesari" in keys(chart(Moon=(2, 2), Jupiter=(5, 5)))   # the 4th from the Moon
    assert "gajakesari" in keys(chart(Moon=(2, 2), Jupiter=(2, 2)))   # with the Moon
    assert "gajakesari" not in keys(chart(Moon=(2, 2), Jupiter=(3, 3)))


def test_budhaditya_and_chandra_mangal_need_the_same_sign():
    assert "budhaditya" in keys(chart(Sun=(4, 4), Mercury=(4, 4)))
    assert "budhaditya" not in keys(chart(Sun=(4, 4), Mercury=(5, 5)))
    assert "chandra_mangal" in keys(chart(Moon=(7, 7), Mars=(7, 7)))


def test_pancha_mahapurusha_needs_own_or_high_sign_and_a_pillar_house():
    c = chart()
    for p in c["planets"]:
        if p["key"] == "Jupiter":
            p.update(sign=4, house=4, dignity="exalted")
    assert "hamsa" in keys(c)
    for p in c["planets"]:
        if p["key"] == "Jupiter":
            p.update(house=3)
    assert "hamsa" not in keys(c)


def test_kaal_sarp_is_all_seven_planets_on_one_side_of_rahu_and_ketu():
    base = {"Rahu": (1, 1), "Ketu": (7, 7)}
    one_side = chart(Sun=(2, 2), Moon=(3, 3), Mars=(4, 4), Mercury=(4, 4), Jupiter=(5, 5), Venus=(6, 6), Saturn=(6, 6), **base)
    assert "kaal_sarp" in keys(one_side)
    split = chart(Sun=(2, 2), Moon=(3, 3), Mars=(4, 4), Mercury=(4, 4), Jupiter=(5, 5), Venus=(6, 6), Saturn=(9, 9), **base)
    assert "kaal_sarp" not in keys(split)


def test_each_found_yoga_has_text_and_a_kind():
    c = chart(Mars=(1, 1), Sun=(4, 4), Mercury=(4, 4))
    for f in y.detect(c, NOW):
        assert f["key"] in yoga_text.TEXT and f["kind"] in ("yoga", "dosha", "phase") and f["planets"]


# ---- the wording ----

def test_the_wording_is_in_both_languages_gentle_and_never_calls_anything_a_fate():
    for key, t in yoga_text.TEXT.items():
        assert t["name"][0] and t["name"][1] and t["en"] and t["hi"], key
        assert not BANNED_EN.search(t["en"]) and not BANNED_HI.search(t["hi"]), key
        assert re.search(r"[ऀ-ॿ]", t["hi"]) and not re.search(r"[A-Za-z]", t["hi"]), key
    assert yoga_text.STATUS == "draft"
    assert set(yoga_text.LEVELS) == {"strong", "steady", "tender"}
    for dosha in ("mangal_dosha", "kaal_sarp", "sade_sati"):  # the doshas are traditional readings, never a fate
        assert "fate" not in yoga_text.TEXT[dosha]["en"].lower() and "destiny" not in yoga_text.TEXT[dosha]["en"].lower(), dosha


def test_the_chart_endpoint_has_strength_aspects_and_yogas(client):
    k = client.post("/v1/kundli", json={"date": "1996-08-14", "time": "07:45", "lat": 18.52, "lon": 73.86,
                                        "tz": "Asia/Kolkata"}).json()
    for p in k["planets"]:
        assert p["strength"]["level"] in ("strong", "steady", "tender") and p["strength"]["name"]["hi"]
        assert all(1 <= h <= 12 for h in p["aspects"]["houses"]) and (p["house"] + 5) % 12 + 1 in p["aspects"]["houses"]
    for yg in k["yogas"]:
        assert yg["name"]["en"] and yg["text"]["hi"] and yg["status"] == "draft"
    assert isinstance(k["yogas"], list)
