import pytest
from sqlalchemy import func, select

from astrodaily.api.daily_text_routes import get_daily_llm_client
from astrodaily.calc import zodiac
from astrodaily.chat.llm import LlmError
from astrodaily.horoscope import love_reading
from astrodaily.main import app
from astrodaily.models import LoveReading, Place

from test_daily_text import FakeLlm, login, profile, use_llm


@pytest.fixture
def ready(client):
    with client.session_factory() as db:
        db.add(Place(id=1273294, name="Delhi", name_hi="दिल्ली", state="Delhi", district="Central Delhi",
                     country_code="IN", latitude=28.65195, longitude=77.23149, population=11034555,
                     timezone="Asia/Kolkata"))
        db.commit()
    h = login(client)
    p = profile(client, h)
    yield client, h, p
    app.dependency_overrides.pop(get_daily_llm_client, None)


def get(api, h, **q):
    return api.get("/v1/me/reading/love", headers=h, params=q)


def rows(api):
    with api.session_factory() as db:
        return db.scalar(select(func.count(LoveReading.id)))


def test_requires_login_consent_and_a_profile(client):
    assert client.get("/v1/me/reading/love").status_code == 401
    assert get(client, login(client, "nocons", consent=False)).status_code == 403
    assert get(client, login(client, "noprofile")).status_code == 404


def test_built_once_then_saved(ready):
    api, h, _ = ready
    llm = use_llm(FakeLlm("First reading.", "Second reading."))
    a = get(api, h)
    assert a.status_code == 200, a.text
    assert a.json()["text"] == "First reading." and a.json()["status"] == "draft" and a.json()["disclaimer"]["en"]
    assert get(api, h).json()["text"] == "First reading."
    assert len(llm.calls) == 1 and rows(api) == 1


def test_each_language_is_its_own(ready):
    api, h, _ = ready
    llm = use_llm(FakeLlm("English reading.", "हिंदी पाठ।"))
    assert get(api, h).json()["text"] == "English reading."
    assert get(api, h, lang="hi").json()["text"] == "हिंदी पाठ।"
    assert "Hindi" in llm.calls[1][0] and rows(api) == 2


def test_needs_the_birth_time(client):
    with client.session_factory() as db:
        db.add(Place(id=1273294, name="Delhi", name_hi="दिल्ली", state="Delhi", district="Central Delhi",
                     country_code="IN", latitude=28.65195, longitude=77.23149, population=11034555,
                     timezone="Asia/Kolkata"))
        db.commit()
    h = login(client)
    r = client.post("/v1/profiles", headers=h, json={"label": "Me", "birth_date": "1990-05-15", "moon_sign": 9, "place_id": 1273294})
    assert r.status_code == 201, r.text
    llm = use_llm(FakeLlm())
    try:
        assert get(client, h).status_code == 409 and llm.calls == []
    finally:
        app.dependency_overrides.pop(get_daily_llm_client, None)


def test_model_unavailable_saves_nothing_and_the_next_open_tries_again(ready):
    api, h, _ = ready
    use_llm(FakeLlm(error=LlmError("network")))
    assert get(api, h).status_code == 503 and rows(api) == 0
    use_llm(None)
    assert get(api, h).status_code == 503
    use_llm(FakeLlm("It works now."))
    assert get(api, h).json()["text"] == "It works now."


def test_a_reply_that_keeps_breaking_the_tone_rules_is_never_saved(ready):
    api, h, _ = ready
    llm = use_llm(FakeLlm("You will definitely get rich.", "A calm, caring pairing."))
    assert get(api, h).json()["text"] == "A calm, caring pairing." and len(llm.calls) == 2
    use_llm(FakeLlm("You will definitely get rich."))
    h2 = login(api, "bob")
    profile(api, h2)
    assert get(api, h2).status_code == 503 and rows(api) == 1


def test_changing_birth_details_throws_it_away_and_a_label_change_keeps_it(ready):
    api, h, p = ready
    llm = use_llm(FakeLlm("Old reading.", "New reading."))
    get(api, h)
    assert api.patch(f"/v1/profiles/{p['id']}", headers=h, json={"label": "Me"}).status_code == 200
    assert rows(api) == 1
    assert api.patch(f"/v1/profiles/{p['id']}", headers=h, json={"birth_time": "11:30"}).status_code == 200
    assert rows(api) == 0
    assert get(api, h).json()["text"] == "New reading." and len(llm.calls) == 2


def test_the_model_gets_chart_facts_and_no_personal_details(ready):
    api, h, _ = ready
    llm = use_llm(FakeLlm())
    get(api, h)
    system = llm.calls[0][0]
    for needle in ("Ascendant (lagna)", "7th house of partnership", "Venus (love", "Darakaraka", "Navamsa (D9", "110 to 150 words"):
        assert needle in system, needle
    for secret in ("SecretLabel", "alice", "example.com", "1990", "10:00", "28.65", "77.23", "Delhi"):
        assert secret not in system, f"{secret!r} leaked to the model"


def test_it_is_in_the_export_and_goes_with_the_account(ready):
    api, h, _ = ready
    use_llm(FakeLlm("Exported reading."))
    get(api, h)
    assert [x["text"] for x in api.get("/v1/me/export", headers=h).json()["love_readings"]] == ["Exported reading."]
    assert api.delete("/v1/me", headers=h).status_code == 204
    assert rows(api) == 0


def chart(lagna, venus_sign=2, venus_house=2, nav_lagna=6):
    def planet(key, sign, deg):
        return {"key": key, "sign": sign, "house": (sign - lagna) % 12 + 1, "degree_in_sign": deg, "dignity": None,
                "retrograde": False, "navamsa_sign": 8}
    planets = [planet("Sun", 1, 10.0), planet("Moon", 4, 20.0), planet("Mars", 7, 5.0), planet("Mercury", 3, 15.0),
               planet("Jupiter", 9, 12.0), planet("Venus", venus_sign, 2.5), planet("Saturn", 10, 25.0),
               planet("Rahu", 11, 0.1), planet("Ketu", 5, 0.1)]
    return {"lagna": {"sign": lagna, "navamsa_sign": nav_lagna}, "planets": planets}


def test_facts_are_worked_out_from_the_chart():
    # Lagna Aries: 7th house is Libra (ruled by Venus). Mars (Libra, house 7) is the only planet there. Mars is not in Karakas' lowest.
    text = love_reading.facts(chart(1, venus_sign=2))
    assert "Ascendant (lagna): Aries." in text
    assert "7th house of partnership: Libra, ruled by Venus. Venus is in Taurus (house 2)." in text
    assert "Planets in the 7th house: Mars." in text
    # Venus has the fewest degrees (2.5), so it is the Darakaraka.
    assert "Darakaraka, the planet with the fewest degrees in its sign): Venus, in Taurus" in text
    # Navamsa lagna Virgo: its 7th is Pisces, ruled by Jupiter; Venus is in the Navamsa sign 8 = Scorpio.
    assert "lagna Virgo; its 7th house is Pisces, ruled by Jupiter; Venus is in Scorpio." in text
    assert text.count("\n") == 5 and zodiac.SIGNS[0][0] == "Aries"
    assert "1990" not in text
