import pytest

from astrodaily.calc import zodiac
from astrodaily.main import app  # noqa: F401
from astrodaily.models import Place
from test_daily_text import login, profile


@pytest.fixture
def ready(client):
    with client.session_factory() as db:
        db.add(Place(id=1273294, name="Delhi", name_hi="दिल्ली", state="Delhi", district="Central Delhi",
                     country_code="IN", latitude=28.65195, longitude=77.23149, population=11034555,
                     timezone="Asia/Kolkata"))
        db.commit()
    h = login(client)
    return client, h, profile(client, h)


def get(api, h, pid, kind):
    return api.get(f"/v1/profiles/{pid}/chart/{kind}", headers=h)


def test_requires_login_consent_and_your_own_profile(ready):
    api, h, p = ready
    assert api.get(f"/v1/profiles/{p['id']}/chart/navamsa").status_code == 401
    assert get(api, login(api, "nocons", consent=False), p["id"], "navamsa").status_code == 403
    assert get(api, login(api, "bob"), p["id"], "navamsa").status_code in (403, 404)
    assert get(api, h, p["id"], "bogus").status_code == 422


def test_each_chart_has_nine_planets_each_with_a_reading(ready):
    api, h, p = ready
    for kind in ("moon", "navamsa", "saptamsa", "dashamsa"):
        r = get(api, h, p["id"], kind)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["kind"] == kind and len(j["planets"]) == 9
        for pl in j["planets"]:
            assert 1 <= pl["house"] <= 12 and pl["sign"]["en"] and pl["sign"]["hi"]
            assert pl["meaning"]["in_sign"]["en"] and pl["meaning"]["in_house"]["en"].startswith(f"In house {pl['house']}")
        assert (j["lagna_meaning"] is None) == (kind == "moon")


def test_the_numbers_match_the_kundli(ready):
    api, h, p = ready
    k = api.get(f"/v1/profiles/{p['id']}/kundli", headers=h).json()
    by = {pl["key"]: pl for pl in k["planets"]}
    for kind, field in (("navamsa", "navamsa_sign"), ("saptamsa", "saptamsa_sign"), ("dashamsa", "dashamsa_sign")):
        j = get(api, h, p["id"], kind).json()
        lagna = k["lagna"][field]["number"]
        assert j["lagna"]["number"] == lagna
        for pl in j["planets"]:
            sign = by[pl["key"]][field]["number"]
            assert pl["sign"]["number"] == sign and pl["house"] == (sign - lagna) % 12 + 1
    moon = get(api, h, p["id"], "moon").json()
    moon_sign = by["Moon"]["sign"]["number"]
    assert moon["lagna"]["number"] == moon_sign
    mo = next(pl for pl in moon["planets"] if pl["key"] == "Moon")
    assert mo["house"] == 1 and mo["sign"]["number"] == moon_sign
    for pl in moon["planets"]:
        assert pl["sign"]["number"] == by[pl["key"]]["sign"]["number"]  # the signs do not change, only the counting
    assert zodiac.SIGNS[moon_sign - 1][0] == moon["lagna"]["en"]


def test_needs_the_birth_time(client):
    with client.session_factory() as db:
        db.add(Place(id=1273294, name="Delhi", name_hi="दिल्ली", state="Delhi", district="Central Delhi",
                     country_code="IN", latitude=28.65195, longitude=77.23149, population=11034555,
                     timezone="Asia/Kolkata"))
        db.commit()
    h = login(client)
    r = client.post("/v1/profiles", headers=h, json={"label": "Me", "birth_date": "1990-05-15", "moon_sign": 9,
                                                     "place_id": 1273294})
    assert get(client, h, r.json()["id"], "navamsa").status_code == 409
