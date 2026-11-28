import re

import pytest

from astrodaily.calc import zodiac
from astrodaily.calc.kundli import names_pair
from astrodaily.config import get_settings
from astrodaily.content import chart_meanings as cm
from astrodaily.content.lint import BANNED_EN, BANNED_HI

PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
DEVANAGARI = re.compile(r"[ऀ-ॿ]")
LATIN = re.compile(r"[A-Za-z]")


def sign_name(n):
    return names_pair(zodiac.SIGNS[n - 1])


def all_meanings():
    for p in PLANETS:
        for s in range(1, 13):
            for h in range(1, 13):
                yield p, s, h, cm.planet_meaning(p, s, sign_name(s), h)
    for s in range(1, 13):
        yield "Lagna", s, None, cm.lagna_meaning(s)


def texts(m):
    for part in (m.about, m.in_sign, m.in_house):
        if part:
            yield part["en"], part["hi"]


def test_every_planet_sign_and_house_has_text_in_both_languages():
    n = 0
    for key, s, h, m in all_meanings():
        assert m is not None, (key, s, h)
        assert m.in_sign["en"].strip() and m.in_sign["hi"].strip()
        assert (m.in_house is None) == (key == "Lagna")
        n += 1
    assert n == 9 * 144 + 12


def test_the_sign_and_house_are_the_ones_asked_for():
    m = cm.planet_meaning("Mars", 8, sign_name(8), 10)
    assert "Scorpio" in m.in_sign["en"] and "house 10" in m.in_house["en"] and "career" in m.in_house["en"]
    assert "वृश्चिक" in m.in_sign["hi"] and "दसवें भाव" in m.in_house["hi"]
    assert "energy, courage and drive" in m.in_house["en"] and "ऊर्जा, साहस और उत्साह" in m.in_house["hi"]
    assert m.in_house != cm.planet_meaning("Venus", 8, sign_name(8), 10).in_house
    assert "Mars" in m.about["en"] and "मंगल" in m.about["hi"]


def test_hand_written_lines_win_for_sun_moon_and_lagna():
    assert cm.planet_meaning("Sun", 1, sign_name(1), 1).in_sign["en"].startswith("Bold, direct")
    assert cm.lagna_meaning(5).in_sign["en"].startswith("You come across as confident")
    assert "In Aries" in cm.planet_meaning("Venus", 1, sign_name(1), 1).in_sign["en"]


def test_wording_follows_the_tone_rules_and_the_language_rules():
    seen = set()
    for key, s, h, m in all_meanings():
        for en, hi in texts(m):
            assert not BANNED_EN.search(en), en
            assert not BANNED_HI.search(hi), hi
            assert not DEVANAGARI.search(en), en
            assert DEVANAGARI.search(hi) and not LATIN.search(hi), hi
            assert "{" not in en + hi and "  " not in en + hi
            seen.add(en)
    assert len(seen) == 238  # each planet has its own lines, not one sentence repeated


def test_unknown_inputs_give_nothing():
    assert cm.planet_meaning("Pluto", 1, sign_name(1), 1) is None
    assert cm.planet_meaning("Sun", 13, sign_name(1), 1) is None
    assert cm.planet_meaning("Sun", 1, sign_name(1), 0) is None
    assert cm.lagna_meaning(0) is None


def test_status_is_draft_and_can_be_hidden_until_reviewed(monkeypatch):
    assert cm.planet_meaning("Mars", 1, sign_name(1), 1).status == "draft"
    monkeypatch.setenv("CHART_MEANINGS_ALLOW_DRAFT", "false")
    get_settings.cache_clear()
    try:
        assert cm.planet_meaning("Mars", 1, sign_name(1), 1) is None
        assert cm.lagna_meaning(1) is None
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


def test_reviewed_groups_make_a_reviewed_line(monkeypatch):
    d = {k: dict(v) if isinstance(v, dict) else v for k, v in cm._data().items()}
    d["status"] = {g: "reviewed" for g in d["status"]}
    monkeypatch.setattr(cm, "_data", lambda: d)
    monkeypatch.setenv("CHART_MEANINGS_ALLOW_DRAFT", "false")
    get_settings.cache_clear()
    try:
        assert cm.planet_meaning("Mars", 1, sign_name(1), 1).status == "reviewed"
        d["status"]["house_area"] = "draft"  # one part still draft: the whole line is draft, so hidden
        assert cm.planet_meaning("Mars", 1, sign_name(1), 1) is None
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


def test_the_chart_endpoint_carries_the_meanings(client):
    r = client.post("/v1/kundli", json={"date": "1996-08-14", "time": "07:45", "lat": 18.52, "lon": 73.86,
                                        "tz": "Asia/Kolkata"})
    assert r.status_code == 200, r.text
    k = r.json()
    assert len(k["planets"]) == 9 and all(p["meaning"] for p in k["planets"])
    sun = next(p for p in k["planets"] if p["key"] == "Sun")
    assert sun["meaning"]["status"] == "draft" and sun["meaning"]["in_house"]["en"].startswith(f"In house {sun['house']}")
    assert k["lagna"]["meaning"]["in_house"] is None and k["lagna"]["meaning"]["about"]["en"]


# ---- what a dasha (period) is like ----

DASHA_LORDS = ["Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury", "Ketu", "Venus"]


def test_every_main_period_has_text_in_both_languages_that_passes_the_tone_rules():
    for lord in DASHA_LORDS:
        m = cm.dasha_meaning(lord)
        assert m and m["en"] and m["hi"], lord
        assert not BANNED_EN.search(m["en"]) and not BANNED_HI.search(m["hi"]), lord
        assert re.search(r"[ऀ-ॿ]", m["hi"]) and not re.search(r"[A-Za-z]", m["hi"]), lord
        assert zodiac.PLANET_NAMES[lord][0] in m["en"], lord


def test_a_sub_period_is_put_together_from_the_two_planets():
    m = cm.dasha_meaning("Rahu", "Mars")
    assert "Rahu" in m["en"] and "Mars" in m["en"] and "ambition" in m["en"] and "energy" in m["en"]
    assert "राहु" in m["hi"] and "मंगल" in m["hi"] and not re.search(r"[A-Za-z]", m["hi"])
    assert cm.dasha_meaning("Pluto") is None and cm.dasha_meaning("Rahu", "Pluto") is None


def test_draft_dasha_text_is_hidden_unless_allowed(monkeypatch):
    monkeypatch.setenv("CHART_MEANINGS_ALLOW_DRAFT", "false")
    get_settings.cache_clear()
    try:
        assert cm.dasha_meaning("Sun") is None and cm.dasha_meaning("Sun", "Moon") is None
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


def test_the_chart_endpoint_carries_what_each_period_is_like(client):
    k = client.post("/v1/kundli", json={"date": "1996-08-14", "time": "07:45", "lat": 18.52, "lon": 73.86,
                                        "tz": "Asia/Kolkata"}).json()
    for m in k["dasha"]["mahadashas"]:
        assert m["meaning"]["en"] and m["meaning"]["hi"]
        assert len(m["antardashas"]) == 9 and all(a["meaning"]["en"] and a["meaning"]["hi"] for a in m["antardashas"])
        assert m["lord"]["en"] in m["meaning"]["en"]
        assert all(m["lord"]["en"] in a["meaning"]["en"] and a["lord"]["en"] in a["meaning"]["en"] for a in m["antardashas"])
