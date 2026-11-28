import json
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from astrodaily.api.daily_text_routes import get_daily_llm_client
from astrodaily.chat.llm import LlmError
from astrodaily.horoscope import planet_cards, service
from astrodaily.main import app
from astrodaily.models import DailyPlanetCards, Place
from test_daily_text import FakeLlm, login, profile, use_llm

GOOD = {a: {"headline": f"Headline {a}.", "message": f"A calm message for {a}."} for a in planet_cards.AREAS}


def reply(texts=None):
    return json.dumps(texts or GOOD)


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
    return api.get("/v1/me/horoscope/planets", headers=h, params=q)


def rows(api):
    with api.session_factory() as db:
        return db.scalar(select(func.count(DailyPlanetCards.id)))


def today():
    return service.today_in("Asia/Kolkata")


def test_requires_login_consent_and_a_profile(client):
    assert client.get("/v1/me/horoscope/planets").status_code == 401
    assert get(client, login(client, "nocons", consent=False)).status_code == 403
    assert get(client, login(client, "noprofile")).status_code == 404


def test_five_cards_one_per_area_each_with_its_planet_sign_house_score_and_lines(ready):
    api, h, _ = ready
    use_llm(FakeLlm(reply()))
    r = get(api, h)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["date"] == today().isoformat() and j["lang"] == "en" and j["disclaimer"]["en"]
    assert [(c["area"], c["planet"]) for c in j["cards"]] == [("career", "Saturn"), ("money", "Jupiter"),
                                                              ("relationships", "Venus"), ("health", "Mars"),
                                                              ("mind", "Mercury")]
    for c in j["cards"]:
        assert 1 <= c["sign"]["number"] <= 12 and c["sign"]["en"] and c["sign"]["hi"] and 1 <= c["house"] <= 12
        assert 1 <= c["score"] <= 5 and c["area_name"]["hi"] and c["planet_name"]["hi"]
        assert c["headline"] == f"Headline {c['area']}." and c["message"] == f"A calm message for {c['area']}."
        assert c["meaning"]["in_sign"]["en"] and c["meaning"]["in_house"]["en"] and c["status"] == "draft"


def test_the_planet_and_house_match_the_birth_chart(ready):
    api, h, p = ready
    use_llm(FakeLlm(reply()))
    cards = {c["planet"]: c for c in get(api, h).json()["cards"]}
    kundli = api.get(f"/v1/profiles/{p['id']}/kundli", headers=h).json()
    for planet in kundli["planets"]:
        if planet["key"] in cards:
            assert cards[planet["key"]]["sign"]["number"] == planet["sign"]["number"]
            assert cards[planet["key"]]["house"] == planet["house"]


def test_built_once_then_saved_and_each_day_and_language_is_its_own(ready):
    api, h, _ = ready
    llm = use_llm(FakeLlm(reply(), reply({a: {"headline": "H", "message": "M"} for a in planet_cards.AREAS}), reply()))
    get(api, h)
    get(api, h)
    assert len(llm.calls) == 1 and rows(api) == 1
    get(api, h, lang="hi")
    get(api, h, date=(today() + timedelta(days=1)).isoformat())
    assert len(llm.calls) == 3 and rows(api) == 3
    assert "Hindi" in llm.calls[1][0]


def test_only_today_and_tomorrow(ready):
    api, h, _ = ready
    llm = use_llm(FakeLlm(reply()))
    for d in (today() - timedelta(days=1), today() + timedelta(days=2)):
        assert get(api, h, date=d.isoformat()).status_code == 422
    assert llm.calls == []


def test_json_in_a_code_fence_is_accepted_but_anything_else_is_retried_then_refused(ready):
    api, h, _ = ready
    use_llm(FakeLlm("```json\n" + reply() + "\n```"))
    assert get(api, h).status_code == 200
    h2 = login(api, "bob")
    profile(api, h2)
    llm = use_llm(FakeLlm("Sorry, here are your cards: not JSON", reply()))
    assert get(api, h2).status_code == 200 and len(llm.calls) == 2  # the second try was good
    h3 = login(api, "carol")
    profile(api, h3)
    bad = {**GOOD, "mind": {"headline": "x"}}  # a card is missing its message
    use_llm(FakeLlm(reply(bad)))
    assert get(api, h3).status_code == 503
    assert rows(api) == 2


def test_a_line_that_breaks_the_tone_rules_is_retried_and_never_saved(ready):
    api, h, _ = ready
    broken = {**GOOD, "money": {"headline": "You will definitely get rich.", "message": "Money is coming."}}
    llm = use_llm(FakeLlm(reply(broken), reply()))
    assert get(api, h).status_code == 200 and len(llm.calls) == 2
    h2 = login(api, "bob")
    profile(api, h2)
    use_llm(FakeLlm(reply(broken)))
    assert get(api, h2).status_code == 503 and rows(api) == 1


def test_model_unavailable_or_not_configured_saves_nothing(ready):
    api, h, _ = ready
    use_llm(FakeLlm(error=LlmError("network")))
    assert get(api, h).status_code == 503 and rows(api) == 0
    use_llm(None)
    assert get(api, h).status_code == 503
    use_llm(FakeLlm(reply()))
    assert get(api, h).status_code == 200


def test_needs_the_birth_time(client):
    with client.session_factory() as db:
        db.add(Place(id=1273294, name="Delhi", name_hi="दिल्ली", state="Delhi", district="Central Delhi",
                     country_code="IN", latitude=28.65195, longitude=77.23149, population=11034555,
                     timezone="Asia/Kolkata"))
        db.commit()
    h = login(client)
    assert client.post("/v1/profiles", headers=h, json={"label": "Me", "birth_date": "1990-05-15", "moon_sign": 9,
                                                        "place_id": 1273294}).status_code == 201
    llm = use_llm(FakeLlm(reply()))
    try:
        assert get(client, h).status_code == 409 and llm.calls == []
    finally:
        app.dependency_overrides.pop(get_daily_llm_client, None)


def test_changing_birth_details_throws_the_cards_away_and_a_label_change_keeps_them(ready):
    api, h, p = ready
    use_llm(FakeLlm(reply()))
    get(api, h)
    assert api.patch(f"/v1/profiles/{p['id']}", headers=h, json={"label": "Me"}).status_code == 200
    assert rows(api) == 1
    assert api.patch(f"/v1/profiles/{p['id']}", headers=h, json={"birth_time": "11:30"}).status_code == 200
    assert rows(api) == 0


def test_the_model_gets_the_planets_and_scores_and_no_personal_details(ready):
    api, h, _ = ready
    llm = use_llm(FakeLlm(reply()))
    get(api, h)
    system = llm.calls[0][0]
    for needle in ("PLANET CARDS", "Saturn in", "Jupiter in", "Venus in", "Mars in", "Mercury in", "out of 5", "headline"):
        assert needle in system or needle.lower() in system.lower(), needle
    for secret in ("SecretLabel", "alice", "example.com", "1990", "10:00", "28.65", "77.23"):
        assert secret not in system, f"{secret!r} leaked to the model"


def test_it_is_in_the_export_and_goes_with_the_account(ready):
    api, h, _ = ready
    use_llm(FakeLlm(reply()))
    get(api, h)
    exp = api.get("/v1/me/export", headers=h).json()
    assert [x["texts"]["career"]["headline"] for x in exp["planet_cards"]] == ["Headline career."]
    assert api.delete("/v1/me", headers=h).status_code == 204
    assert rows(api) == 0


def test_parse_texts_rejects_the_wrong_shapes():
    assert planet_cards.parse_texts("[]") is None
    assert planet_cards.parse_texts("not json") is None
    assert planet_cards.parse_texts(json.dumps({**GOOD, "health": "text"})) is None
    assert planet_cards.parse_texts(json.dumps({**GOOD, "health": {"headline": " ", "message": "m"}})) is None
    assert planet_cards.parse_texts(reply()) == GOOD


# ---- the planet widget ----

def wtoken(api, h):
    r = api.post("/v1/me/widget-token", headers=h)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def wplanets(api, token, **q):
    return api.get("/v1/widget/planets", headers={"Authorization": f"Bearer {token}"}, params=q)


def test_the_widget_token_reads_the_same_five_cards_as_the_app(ready):
    api, h, _ = ready
    llm = use_llm(FakeLlm(reply()))
    from_app = get(api, h).json()
    r = wplanets(api, wtoken(api, h))
    assert r.status_code == 200, r.text
    assert r.json() == from_app
    assert len(llm.calls) == 1 and rows(api) == 1  # the widget did not write them again


def test_the_widget_endpoint_needs_a_widget_token_not_a_session_and_consent(ready):
    api, h, _ = ready
    use_llm(FakeLlm(reply()))
    assert api.get("/v1/widget/planets").status_code == 401
    session = h["Authorization"].split()[1]
    assert wplanets(api, session).status_code == 401  # a session token is not a widget token
    token = wtoken(api, h)
    assert api.get("/v1/me/horoscope/planets", headers={"Authorization": f"Bearer {token}"}).status_code == 401  # nor the other way
    assert wplanets(api, token, lang="hi").status_code == 200


def test_the_widget_gets_409_without_a_birth_time(client):
    with client.session_factory() as db:
        db.add(Place(id=1273294, name="Delhi", name_hi="दिल्ली", state="Delhi", district="Central Delhi",
                     country_code="IN", latitude=28.65195, longitude=77.23149, population=11034555,
                     timezone="Asia/Kolkata"))
        db.commit()
    h = login(client)
    assert client.post("/v1/profiles", headers=h, json={"label": "Me", "birth_date": "1990-05-15", "moon_sign": 9,
                                                        "place_id": 1273294}).status_code == 201
    use_llm(FakeLlm(reply()))
    try:
        assert wplanets(client, wtoken(client, h)).status_code == 409
    finally:
        app.dependency_overrides.pop(get_daily_llm_client, None)
