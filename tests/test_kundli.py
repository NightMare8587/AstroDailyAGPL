from datetime import date, datetime, time, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from astrodaily.calc import dasha, ephem, names, zodiac
from astrodaily.calc.kundli import compute_chart, resolve_birth_moment
from astrodaily.calc.panchang import compute_panchang
from astrodaily.main import app

client = TestClient(app)
DELHI = (28.6139, 77.209)

# ---------- zodiac ----------

def test_navamsa_known_values():
    assert zodiac.navamsa_sign(0.0) == 1            # Aries 0: Aries
    assert zodiac.navamsa_sign(3.34) == 2           # second part of Aries: Taurus
    assert zodiac.navamsa_sign(26.7) == 9           # last part of Aries: Sagittarius
    assert zodiac.navamsa_sign(30.0) == 10          # Taurus (fixed) starts at Capricorn
    assert zodiac.navamsa_sign(60.0) == 7           # Gemini (dual) starts at Libra
    assert zodiac.navamsa_sign(90.0) == 4           # Cancer (movable) starts at Cancer
    assert zodiac.navamsa_sign(359.99) == 12        # last part of Pisces (dual, from Cancer) ends in Pisces


def test_dignities():
    assert zodiac.dignity("Sun", 1) == "exalted" and zodiac.dignity("Sun", 7) == "debilitated"
    assert zodiac.dignity("Moon", 2) == "exalted" and zodiac.dignity("Moon", 8) == "debilitated"
    assert zodiac.dignity("Mars", 10) == "exalted" and zodiac.dignity("Mars", 4) == "debilitated"
    assert zodiac.dignity("Jupiter", 4) == "exalted" and zodiac.dignity("Jupiter", 10) == "debilitated"
    assert zodiac.dignity("Saturn", 7) == "exalted" and zodiac.dignity("Saturn", 1) == "debilitated"
    assert zodiac.dignity("Venus", 12) == "exalted" and zodiac.dignity("Venus", 6) == "debilitated"
    assert zodiac.dignity("Mercury", 6) == "exalted" and zodiac.dignity("Mercury", 12) == "debilitated"
    assert zodiac.dignity("Saturn", 10) == "own" and zodiac.dignity("Saturn", 11) == "own"
    assert zodiac.dignity("Mars", 1) == "own" and zodiac.dignity("Mars", 8) == "own"
    assert zodiac.dignity("Rahu", 2) is None and zodiac.dignity("Sun", 3) is None


# ---------- Vimshottari ----------

BIRTH = datetime(2000, 1, 1, 6, 0, tzinfo=timezone.utc)
SPAN = 360 / 27


def test_dasha_cycle_totals_and_order():
    assert sum(dasha.YEARS.values()) == 120
    assert [dasha.nakshatra_lord(i) for i in (0, 1, 2, 3, 8, 9, 18, 26)] == \
        ["Ketu", "Venus", "Sun", "Moon", "Mercury", "Ketu", "Ketu", "Mercury"]
    _, periods = dasha.mahadashas(10.0, BIRTH)
    assert [p.lord for p in periods] == ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
    assert all(a.end == b.start for a, b in zip(periods, periods[1:]))
    total = periods[-1].end - periods[0].start
    assert abs(total.days - 120 * 365.25) < 1


def test_balance_at_birth():
    bal, periods = dasha.mahadashas(0.0, BIRTH)             # Moon at the very start of Ashwini
    assert bal.lord == "Ketu" and bal.fraction_elapsed == 0 and bal.years_remaining == 7
    assert periods[0].start == BIRTH                          # nothing has elapsed
    bal, periods = dasha.mahadashas(SPAN / 2, BIRTH)         # halfway through Ashwini
    assert bal.years_remaining == pytest.approx(3.5)
    assert (BIRTH - periods[0].start).total_seconds() / 86400 == pytest.approx(3.5 * 365.25, abs=1e-6)
    bal, _ = dasha.mahadashas(SPAN * 3 + SPAN * 0.25, BIRTH)  # a quarter through Rohini: Moon dasha
    assert bal.lord == "Moon" and bal.years_remaining == pytest.approx(7.5)
    bal, _ = dasha.mahadashas(SPAN * 27 - 0.0001, BIRTH)      # end of Revati: Mercury, almost nothing left
    assert bal.lord == "Mercury" and bal.years_remaining == pytest.approx(17 * 0.0001 / SPAN, rel=1e-3)


def test_subperiods_proportions_and_closure():
    _, periods = dasha.mahadashas(SPAN * 1 + 1.0, BIRTH)    # Venus mahadasha first
    venus = periods[0]
    subs = dasha.subperiods(venus)
    assert [s.lord for s in subs][:3] == ["Venus", "Sun", "Moon"]  # starts with the parent's own lord
    assert subs[0].start == venus.start and subs[-1].end == venus.end
    assert all(a.end == b.start for a, b in zip(subs, subs[1:]))
    # Venus-Venus: 20 * 20 / 120 = 3.333 years of the 20-year Venus mahadasha
    assert (subs[0].end - subs[0].start).total_seconds() / 86400 == pytest.approx(20 * 20 / 120 * 365.25, rel=1e-9)
    # Pratyantardashas close the same way.
    pratyas = dasha.subperiods(subs[2])
    assert pratyas[0].lord == subs[2].lord and pratyas[-1].end == subs[2].end


def test_running_dasha_boundaries():
    _, periods = dasha.mahadashas(100.0, BIRTH)
    first = periods[0]
    assert dasha.running(periods, first.start)["mahadasha"] is first            # start is inclusive
    assert dasha.running(periods, first.end)["mahadasha"] is periods[1]         # end is exclusive
    r = dasha.running(periods, BIRTH + timedelta(days=4000))
    assert r["antardasha"].start <= BIRTH + timedelta(days=4000) < r["antardasha"].end
    assert r["pratyantardasha"].start <= BIRTH + timedelta(days=4000) < r["pratyantardasha"].end
    assert dasha.running(periods, periods[-1].end) is None
    assert dasha.running(periods, first.start - timedelta(days=1)) is None


# ---------- birth moment ----------

def test_birth_moment_ist_and_offset_override():
    bm = resolve_birth_moment(date(1990, 5, 15), time(10, 0), "Asia/Kolkata", None)
    assert bm.utc == datetime(1990, 5, 15, 4, 30, tzinfo=timezone.utc) and bm.utc_offset_minutes == 330
    assert bm.warnings == []
    bm = resolve_birth_moment(date(1990, 5, 15), time(10, 0), "Asia/Kolkata", 360)
    assert bm.utc == datetime(1990, 5, 15, 4, 0, tzinfo=timezone.utc) and bm.warnings == []


def test_birth_moment_warnings():
    old = resolve_birth_moment(date(1940, 6, 1), time(10, 0), "Asia/Kolkata", None)
    assert any("1947" in w for w in old.warnings)
    twice = resolve_birth_moment(date(1990, 10, 28), time(1, 30), "Europe/London", None)
    assert any("twice" in w for w in twice.warnings)
    missing = resolve_birth_moment(date(1990, 3, 25), time(1, 30), "Europe/London", None)
    assert any("did not exist" in w for w in missing.warnings)
    assert resolve_birth_moment(date(2000, 1, 1), time(1, 30), "Europe/London", None).warnings == []


# ---------- chart: independent reference values ----------
# Reference numbers come from ndastro-engine (MIT, Skyfield + JPL DE440), a different engine and
# ephemeris from ours. Differences of a few thousandths of a degree are expected.

REFERENCE = [
    {"in": ("1990-05-15", "10:00", 28.6139, 77.209), "lagna": 93.485,
     "planets": {"Sun": 30.3729, "Moon": 269.5903, "Mars": 324.3798, "Mercury": 14.3318,
                 "Jupiter": 75.7608, "Venus": 348.74, "Saturn": 271.5327},
     "maha": [("Sun", "1989-01-19"), ("Moon", "1995-01-20"), ("Mars", "2005-01-19"), ("Rahu", "2012-01-20"),
              ("Jupiter", "2030-01-19"), ("Saturn", "2046-01-19"), ("Mercury", "2065-01-19"),
              ("Ketu", "2082-01-19"), ("Venus", "2089-01-19")]},
    {"in": ("1972-11-22", "05:10", 13.0827, 80.2707), "lagna": 201.418,
     "planets": {"Sun": 216.2958, "Moon": 50.911, "Mars": 190.5346, "Mercury": 225.821,
                 "Jupiter": 255.4693, "Venus": 183.361, "Saturn": 54.9926},
     "maha": [("Moon", "1964-09-16"), ("Mars", "1974-09-16"), ("Rahu", "1981-09-16"), ("Jupiter", "1999-09-16"),
              ("Saturn", "2015-09-16"), ("Mercury", "2034-09-16"), ("Ketu", "2051-09-16"),
              ("Venus", "2058-09-16"), ("Sun", "2078-09-16")]},
    {"in": ("2024-02-29", "12:00", 28.6139, 77.209), "lagna": 53.458,
     "planets": {"Sun": 315.9637, "Moon": 187.4805, "Mars": 288.1587, "Mercury": 316.7546,
                 "Jupiter": 16.9964, "Venus": 291.3966, "Saturn": 315.6302},
     "maha": [("Rahu", "2023-01-23"), ("Jupiter", "2041-01-23"), ("Saturn", "2057-01-23"), ("Mercury", "2076-01-24"),
              ("Ketu", "2093-01-23"), ("Venus", "2100-01-24"), ("Sun", "2120-01-25"),
              ("Moon", "2126-01-24"), ("Mars", "2136-01-25")]},
]


def _angle_diff(a, b):
    return abs((a - b + 180) % 360 - 180)


@pytest.mark.parametrize("case", REFERENCE, ids=lambda c: c["in"][0])
def test_chart_matches_independent_engine(case):
    d, t, lat, lon = case["in"]
    bm = resolve_birth_moment(date.fromisoformat(d), time.fromisoformat(t), "Asia/Kolkata", None)
    chart = compute_chart(bm, lat, lon)
    for p in chart["planets"]:
        if p["key"] in case["planets"]:
            assert _angle_diff(p["longitude"], case["planets"][p["key"]]) < 0.01, p["key"]
    assert _angle_diff(chart["lagna"]["longitude"], case["lagna"]) < 0.1
    mine = [(m["lord"], m["start"].astimezone(timezone.utc).date()) for m in chart["dasha"]["mahadashas"]]
    assert [m[0] for m in mine] == [m[0] for m in case["maha"]]
    for (_, got), (_, want) in zip(mine, case["maha"]):
        assert abs((got - date.fromisoformat(want)).days) <= 4   # the engines differ by up to 3 days


# ---------- chart: structural invariants ----------

def _chart(d="1990-05-15", t="10:00", lat=28.6139, lon=77.209, node="mean"):
    bm = resolve_birth_moment(date.fromisoformat(d), time.fromisoformat(t), "Asia/Kolkata", None)
    return compute_chart(bm, lat, lon, node, datetime(2026, 11, 27, 6, 30, tzinfo=timezone.utc))


def test_chart_invariants():
    ch = _chart()
    planets = {p["key"]: p for p in ch["planets"]}
    assert list(planets) == ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
    assert _angle_diff(planets["Ketu"]["longitude"], planets["Rahu"]["longitude"] + 180) < 1e-9
    assert planets["Rahu"]["retrograde"] and planets["Ketu"]["retrograde"]
    lagna_sign = ch["lagna"]["sign"]
    assert len(ch["houses"]) == 12 and ch["houses"][0]["sign"] == lagna_sign
    assert [h["house"] for h in ch["houses"]] == list(range(1, 13))
    placed = [k for h in ch["houses"] for k in h["planets"]]
    assert sorted(placed) == sorted(planets)  # every planet sits in exactly one house
    for p in planets.values():
        assert p["house"] == (p["sign"] - lagna_sign) % 12 + 1
        assert 0 <= p["degree_in_sign"] < 30 and 1 <= p["pada"] <= 4 and 1 <= p["nakshatra"] <= 27
        assert p["sign"] == int(p["longitude"] // 30) + 1
    assert _angle_diff(planets["Mercury"]["longitude"], planets["Sun"]["longitude"]) < 29   # Mercury stays close to the Sun
    assert _angle_diff(planets["Venus"]["longitude"], planets["Sun"]["longitude"]) < 49


def test_lagna_at_sunrise_is_near_the_sun():
    for d in (date(2025, 1, 10), date(2025, 4, 20), date(2025, 7, 7), date(2025, 10, 30)):
        p = compute_panchang(d, *DELHI, "Asia/Kolkata")
        bm = resolve_birth_moment(d, p["sunrise"].time().replace(microsecond=0), "Asia/Kolkata", None)
        ch = compute_chart(bm, *DELHI)
        sun = next(x for x in ch["planets"] if x["key"] == "Sun")
        assert _angle_diff(ch["lagna"]["longitude"], sun["longitude"]) < 3.0


def test_retrograde_flags_are_plausible():
    # Saturn was retrograde on 15 May 1990 and direct on 15 Feb 1990? Check against speed sign directly.
    jd = ephem.datetime_to_jd(datetime(1990, 5, 15, 4, 30, tzinfo=timezone.utc))
    _, speed = ephem.body_position(jd, ephem.SATURN)
    sat = next(p for p in _chart()["planets"] if p["key"] == "Saturn")
    assert sat["retrograde"] == (speed < 0)
    sun = next(p for p in _chart()["planets"] if p["key"] == "Sun")
    moon = next(p for p in _chart()["planets"] if p["key"] == "Moon")
    assert not sun["retrograde"] and not moon["retrograde"]   # luminaries never retrograde


def test_true_and_mean_node_differ_a_little():
    mean = next(p for p in _chart(node="mean")["planets"] if p["key"] == "Rahu")["longitude"]
    true = next(p for p in _chart(node="true")["planets"] if p["key"] == "Rahu")["longitude"]
    assert 0 < _angle_diff(mean, true) < 2.0


# ---------- API ----------

BODY = {"date": "1990-05-15", "time": "10:00", "lat": 28.6139, "lon": 77.209, "as_of": "2026-11-27"}


def test_api_kundli_shape_and_current_dasha():
    r = client.post("/v1/kundli", json=BODY)
    assert r.status_code == 200, r.text
    k = r.json()
    assert k["birth"]["utc_offset_minutes"] == 330 and k["birth"]["timezone"] == "Asia/Kolkata"
    assert k["birth"]["local_datetime"].endswith("+05:30") and k["warnings"] == []
    assert k["lagna"]["sign"]["en"] == "Cancer" and k["lagna"]["sign"]["hi"] == "कर्क"
    assert len(k["planets"]) == 9 and len(k["houses"]) == 12
    sun = k["planets"][0]
    assert sun["key"] == "Sun" and sun["sign"]["en"] == "Taurus" and sun["name"]["hi"] == "सूर्य"
    assert k["dasha"]["system"] == "vimshottari" and len(k["dasha"]["mahadashas"]) == 9
    assert all(len(m["antardashas"]) == 9 for m in k["dasha"]["mahadashas"])
    cur = k["dasha"]["current"]
    assert cur["mahadasha"]["lord"]["en"] == "Rahu" and cur["antardasha"]["lord"]["en"] == "Sun"
    assert cur["mahadasha"]["start"] <= k["dasha"]["as_of"] < cur["mahadasha"]["end"]
    assert k["dasha"]["balance_at_birth"]["lord"]["en"] == "Sun"


def test_api_as_of_outside_the_cycle_has_no_current_dasha():
    r = client.post("/v1/kundli", json={**BODY, "as_of": "2200-01-01"})
    assert r.status_code == 200 and r.json()["dasha"]["current"] is None


def test_api_utc_offset_override_and_warnings():
    r = client.post("/v1/kundli", json={**BODY, "date": "1940-06-01"})
    assert r.status_code == 200 and any("1947" in w for w in r.json()["warnings"])
    over = client.post("/v1/kundli", json={**BODY, "utc_offset_minutes": 353}).json()
    assert over["birth"]["utc_offset_minutes"] == 353 and over["birth"]["local_datetime"].endswith("+05:53")
    base = client.post("/v1/kundli", json=BODY).json()
    assert over["lagna"]["longitude"] != base["lagna"]["longitude"]


def test_api_node_option():
    mean = client.post("/v1/kundli", json=BODY).json()
    true = client.post("/v1/kundli", json={**BODY, "node": "true"}).json()
    assert mean["node"] == "mean" and true["node"] == "true"
    assert client.post("/v1/kundli", json={**BODY, "node": "bogus"}).status_code == 422


def test_api_validation():
    assert client.post("/v1/kundli", json={"date": "1990-05-15", "time": "10:00"}).status_code == 422  # no place
    assert client.post("/v1/kundli", json={**BODY, "lon": None}).status_code == 422
    assert client.post("/v1/kundli", json={**BODY, "tz": "Mars/Base"}).status_code == 422
    assert client.post("/v1/kundli", json={**BODY, "date": "1700-01-01"}).status_code == 422
    assert client.post("/v1/kundli", json={**BODY, "date": "2500-01-01"}).status_code == 422
    assert client.post("/v1/kundli", json={**BODY, "as_of": "3000-01-01"}).status_code == 422
    assert client.post("/v1/kundli", json={**BODY, "time": "25:00"}).status_code == 422
    assert client.post("/v1/kundli", json={**BODY, "lat": 95}).status_code == 422
    assert client.post("/v1/kundli", json={**BODY, "place_id": 1}).status_code == 422  # both place and coordinates
    assert client.post("/v1/kundli", json={"date": "1990-05-15", "time": "10:00", "place_id": 1}).status_code == 503


def test_api_by_place_id(client):  # uses the database-backed client fixture
    from astrodaily.models import Place
    with client.session_factory() as db:
        db.add(Place(id=1273294, name="Delhi", name_hi="दिल्ली", state="Delhi", district=None, country_code="IN",
                     latitude=28.65195, longitude=77.23149, population=11034555, timezone="Asia/Kolkata"))
        db.commit()
    body = {"date": "1990-05-15", "time": "10:00", "place_id": 1273294, "as_of": "2026-11-27"}
    r = client.post("/v1/kundli", json=body)
    assert r.status_code == 200 and r.json()["birth"]["place"]["name"] == "Delhi"
    assert r.json()["birth"]["latitude"] == pytest.approx(28.65195)
    assert client.post("/v1/kundli", json={**body, "place_id": 5}).status_code == 404
