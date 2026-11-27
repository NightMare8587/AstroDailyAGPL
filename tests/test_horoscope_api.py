from datetime import date, datetime, time, timezone

import pytest
from sqlalchemy import func, select

from astrodaily.calc.kundli import compute_chart, resolve_birth_moment
from astrodaily.horoscope import NatalContext, build_day_report, natal_from_chart, service
from astrodaily.models import BirthProfile, HoroscopeFeedback, Place

DAY = "2025-11-05"


@pytest.fixture
def api(client):
    with client.session_factory() as db:
        db.add_all([
            Place(id=1273294, name="Delhi", name_hi="दिल्ली", state="Delhi", district="Central Delhi",
                  country_code="IN", latitude=28.65195, longitude=77.23149, population=11034555, timezone="Asia/Kolkata"),
            Place(id=1275339, name="Mumbai", state="Maharashtra", district="Mumbai", country_code="IN",
                  latitude=19.07283, longitude=72.88261, population=12691836, timezone="Asia/Kolkata"),
        ])
        db.commit()
    return client


def login(client, sub="alice", consent=True):
    r = client.post("/v1/auth/google", json={"id_token": f"good-{sub}"})
    assert r.status_code == 200, r.text
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    if consent:
        assert client.patch("/v1/me", headers=h, json={"consent_version": "2026-11"}).status_code == 200
    return h


def make_profile(api, h, **over):
    body = {"label": "Me", "birth_date": "1990-05-15", "birth_time": "10:00", "place_id": 1273294, **over}
    r = api.post("/v1/profiles", headers=h, json=body)
    assert r.status_code == 201, r.text
    return r.json()


def ids(card, key="why"):
    return [s["id"] for s in card[key]]


# ---------------------------------------------------------------- by Moon sign (public)

def test_rashi_card_shape_and_bilingual_names(api):
    r = api.get("/v1/horoscope/rashi/5", params={"date": DAY})
    assert r.status_code == 200, r.text
    c = r.json()
    assert c["level"] == "A" and c["subject"] == {"type": "rashi", "rashi": 5,
        "rashi_name": {"en": "Leo", "hi": "सिंह"}, "profile_id": None}
    assert 1 <= c["score"] <= 5 and len(c["areas"]) == 5
    assert c["areas"][0]["name"] == {"en": "Career", "hi": "करियर"}
    assert all(1 <= a["score"] <= 5 for a in c["areas"])
    assert len(c["dos"]) <= 3 and len(c["donts"]) <= 3
    assert c["panchang"]["tithi"]["en"] == "Purnima" and c["panchang"]["vara"]["hi"] == "बुधवार"
    assert any(w["label"] == "Rahu Kaal" for w in c["windows"]["avoid"])
    assert [w["start"] for w in c["windows"]["avoid"]] == sorted(w["start"] for w in c["windows"]["avoid"])
    sunrise, sunset = c["panchang"]["sunrise"], c["panchang"]["sunset"]
    assert all(sunrise <= w["start"] and w["end"] <= sunset for w in c["windows"]["best"])
    assert c["generated_by"] == "rules" and c["engine_version"] and c["ruleset_version"] and c["scoring_version"]
    assert "medical" in c["disclaimer"]["en"] and c["disclaimer"]["hi"]


def test_rashi_card_matches_the_engine_directly(api):
    c = api.get("/v1/horoscope/rashi/9", params={"date": DAY}).json()
    direct = build_day_report(date(2025, 11, 5), 28.6139, 77.2090, "Asia/Kolkata", NatalContext(moon_sign=9))
    assert ids(c) == [s.id for s in direct.signals]
    assert c["score"] == direct.score and {a["key"]: a["score"] for a in c["areas"]} == direct.areas
    assert ids(c, "dos") == [s.id for s in direct.favourable] and ids(c, "donts") == [s.id for s in direct.unfavourable]


def test_all_twelve_rashis_work_and_differ(api):
    cards = [api.get(f"/v1/horoscope/rashi/{n}", params={"date": DAY}).json() for n in range(1, 13)]
    assert [c["subject"]["rashi"] for c in cards] == list(range(1, 13))
    assert len({tuple(ids(c)) for c in cards}) > 6   # the sign changes the card
    assert api.get("/v1/horoscope/rashi/0").status_code == 422
    assert api.get("/v1/horoscope/rashi/13").status_code == 422
    assert api.get("/v1/horoscope/rashi/abc").status_code == 422


def test_rashi_location_choices(api):
    base = {"date": DAY}
    d = api.get("/v1/horoscope/rashi/5", params=base).json()
    assert d["location"]["source"] == "default" and d["location"]["timezone"] == "Asia/Kolkata"
    m = api.get("/v1/horoscope/rashi/5", params={**base, "place_id": 1275339}).json()
    assert m["location"]["source"] == "explicit_place" and m["location"]["place_name"] == "Mumbai, Mumbai, Maharashtra"
    assert m["panchang"]["sunrise"] != d["panchang"]["sunrise"]   # Mumbai sunrise differs from Delhi
    c = api.get("/v1/horoscope/rashi/5", params={**base, "lat": 13.08, "lon": 80.27}).json()
    assert c["location"]["source"] == "coordinates" and c["location"]["place_name"] is None
    r = api.get("/v1/horoscope/rashi/5", params={**base, "lat": 13.08})
    assert r.status_code == 422 and "location" in r.json()["detail"]
    assert api.get("/v1/horoscope/rashi/5", params={**base, "place_id": 999}).status_code == 404
    assert api.get("/v1/horoscope/rashi/5", params={**base, "place_id": 1275339, "lat": 1, "lon": 1}).status_code == 422
    assert api.get("/v1/horoscope/rashi/5", params={**base, "lat": 13.08, "lon": 80.27, "tz": "Mars/Base"}).status_code == 422


def test_rashi_uses_the_signed_in_users_home_city_and_ignores_bad_tokens(api):
    h = login(api)
    api.patch("/v1/me", headers=h, json={"home_place_id": 1275339})
    home = api.get("/v1/horoscope/rashi/5", params={"date": DAY}, headers=h).json()
    assert home["location"]["source"] == "home" and home["location"]["place_name"].startswith("Mumbai")
    over = api.get("/v1/horoscope/rashi/5", params={"date": DAY, "place_id": 1273294}, headers=h).json()
    assert over["location"]["source"] == "explicit_place"          # an explicit place always wins
    stale = api.get("/v1/horoscope/rashi/5", params={"date": DAY}, headers={"Authorization": "Bearer garbage"})
    assert stale.status_code == 200 and stale.json()["location"]["source"] == "default"  # public endpoint


def test_language_is_accepted_and_reported_honestly(api):
    hi = api.get("/v1/horoscope/rashi/5", params={"date": DAY, "lang": "hi"}).json()
    assert hi["requested_language"] == "hi" and hi["text_language"] == "en" and hi["translated"] is False
    assert api.get("/v1/horoscope/rashi/5", params={"date": DAY, "lang": "fr"}).status_code == 422


def test_date_defaults_to_today_at_the_location_and_is_bounded(api):
    c = api.get("/v1/horoscope/rashi/5").json()
    assert c["date"] == service.today_in("Asia/Kolkata").isoformat()
    assert api.get("/v1/horoscope/rashi/5", params={"date": "1700-01-01"}).status_code == 422
    assert api.get("/v1/horoscope/rashi/5", params={"date": "2500-01-01"}).status_code == 422
    assert api.get("/v1/horoscope/rashi/5", params={"date": "not-a-date"}).status_code == 422


def test_cached_core_is_never_mutated_by_different_locations(api):
    a = api.get("/v1/horoscope/rashi/5", params={"date": DAY}).json()
    b = api.get("/v1/horoscope/rashi/5", params={"date": DAY, "place_id": 1275339}).json()
    a2 = api.get("/v1/horoscope/rashi/5", params={"date": DAY}).json()
    assert a == a2 and a["location"]["source"] == "default" and b["location"]["source"] == "explicit_place"


# ---------------------------------------------------------------- personal

def test_personal_cards_need_sign_in_consent_and_ownership(api):
    assert api.get("/v1/me/horoscope").status_code == 401
    assert api.get("/v1/me/horoscope/widget").status_code == 401
    alice, bob = login(api, "alice"), login(api, "bob")
    pid = make_profile(api, alice)["id"]
    assert api.get(f"/v1/profiles/{pid}/horoscope", headers=bob).status_code == 404   # not bob's
    assert api.get(f"/v1/profiles/{pid}/horoscope").status_code == 401
    nocons = login(api, "carol", consent=False)
    assert api.get("/v1/me/horoscope", headers=nocons).status_code == 403
    assert api.get(f"/v1/profiles/{pid}/horoscope", headers=nocons).status_code == 403
    assert api.get(f"/v1/profiles/{pid}/horoscope", headers=alice, params={"date": DAY}).status_code == 200


def test_level_b_card_matches_the_engine_with_the_natal_chart(api):
    h = login(api)
    p = make_profile(api, h)
    c = api.get(f"/v1/profiles/{p['id']}/horoscope", headers=h, params={"date": DAY}).json()
    assert c["level"] == "B" and c["subject"] == {"type": "profile", "rashi": None, "rashi_name": None,
                                                   "profile_id": p["id"]}
    noon = datetime(2025, 11, 5, 6, 30, tzinfo=timezone.utc)
    bm = resolve_birth_moment(date(1990, 5, 15), time(10, 0), "Asia/Kolkata", None)
    chart = compute_chart(bm, 28.65195, 77.23149, "mean", noon)
    direct = build_day_report(date(2025, 11, 5), 28.65195, 77.23149, "Asia/Kolkata", natal_from_chart(chart, as_of=noon))
    assert ids(c) == [s.id for s in direct.signals] and c["score"] == direct.score
    assert any(i.startswith("tara_") for i in ids(c)) and any(i.startswith("dasha_") for i in ids(c))


def test_personal_location_precedence(api):
    h = login(api)
    p = make_profile(api, h)   # born in Delhi
    url, q = f"/v1/profiles/{p['id']}/horoscope", {"date": DAY}
    assert api.get(url, headers=h, params=q).json()["location"]["source"] == "profile"
    api.patch("/v1/me", headers=h, json={"home_place_id": 1275339})
    assert api.get(url, headers=h, params=q).json()["location"]["source"] == "home"
    x = api.get(url, headers=h, params={**q, "place_id": 1273294}).json()
    assert x["location"]["source"] == "explicit_place" and x["location"]["place_name"].startswith("Delhi")


def test_editing_a_profile_never_serves_a_stale_card(api):
    h = login(api)
    p = make_profile(api, h)
    url, q = f"/v1/profiles/{p['id']}/horoscope", {"date": DAY}
    before = api.get(url, headers=h, params=q).json()
    api.patch(f"/v1/profiles/{p['id']}", headers=h, json={"birth_date": "1990-05-22"})
    after = api.get(url, headers=h, params=q).json()
    tara = lambda c: [s["params"]["count"] for s in c["why"] if s["id"].startswith("tara_")]
    assert tara(before) != tara(after)   # a different natal Moon gives a different Tara Bala count


def test_me_card_is_the_first_profile_and_needs_one(api):
    h = login(api)
    r = api.get("/v1/me/horoscope", headers=h, params={"date": DAY})
    assert r.status_code == 404 and "birth profile" in r.json()["detail"]
    assert api.get("/v1/me/horoscope/widget", headers=h).status_code == 404
    first = make_profile(api, h)
    make_profile(api, h, label="Mom", birth_date="1962-03-03")
    me = api.get("/v1/me/horoscope", headers=h, params={"date": DAY}).json()
    direct = api.get(f"/v1/profiles/{first['id']}/horoscope", headers=h, params={"date": DAY}).json()
    assert me == direct and me["subject"]["profile_id"] == first["id"]


def test_widget_payload_is_small_and_consistent(api):
    h = login(api)
    make_profile(api, h)
    w = api.get("/v1/me/horoscope/widget", headers=h, params={"date": DAY})
    assert w.status_code == 200
    body, full = w.json(), api.get("/v1/me/horoscope", headers=h, params={"date": DAY}).json()
    assert set(body) == {"date", "score", "level", "headline", "caution", "best_window", "avoid_window",
                         "timezone", "text_language"}
    assert body["score"] == full["score"] and body["headline"] == full["dos"][0]["reason"]
    assert body["best_window"] == full["windows"]["best"][0] and body["avoid_window"]["label"] == "Rahu Kaal"
    rahu = next(w for w in full["windows"]["avoid"] if w["label"] == "Rahu Kaal")
    assert body["avoid_window"] == rahu
    assert len(w.content) < len(api.get("/v1/me/horoscope", headers=h, params={"date": DAY}).content) / 4


# ---------------------------------------------------------------- feedback

def test_feedback_upserts_and_validates(api):
    h = login(api)
    post = lambda **o: api.post("/v1/horoscope/feedback", headers=h,
                                json={"subject": "rashi:5", "date": DAY, "rating": 1, **o})
    assert api.post("/v1/horoscope/feedback", json={"subject": "rashi:5", "date": DAY, "rating": 1}).status_code == 401
    first = post()
    assert first.status_code == 200 and first.json()["rating"] == 1 and first.json()["felt_accurate"] is None
    again = post(rating=-1, felt_accurate=False)          # re-rating replaces, never duplicates
    assert again.json()["rating"] == -1 and again.json()["felt_accurate"] is False
    with api.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(HoroscopeFeedback)) == 1
    post(date="2025-11-06")                                # another day is another row
    with api.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(HoroscopeFeedback)) == 2
    for bad in ({"rating": 0}, {"rating": 2}, {"subject": "rashi:13"}, {"subject": "rashi:0"},
                {"subject": "rashi:x"}, {"subject": "profile:not-a-uuid"}, {"subject": "foo"}, {"date": "1700-01-01"}):
        assert post(**bad).status_code == 422, bad


def test_feedback_on_profiles_is_owner_only_and_deleted_with_them(api):
    alice, bob = login(api, "alice"), login(api, "bob")
    pid = make_profile(api, alice)["id"]
    body = {"subject": f"profile:{pid}", "date": DAY, "rating": 1}
    assert api.post("/v1/horoscope/feedback", headers=bob, json=body).status_code == 404
    assert api.post("/v1/horoscope/feedback", headers=alice, json=body).status_code == 200
    api.post("/v1/horoscope/feedback", headers=alice, json={"subject": "rashi:5", "date": DAY, "rating": -1})
    api.post("/v1/horoscope/feedback", headers=bob, json={"subject": "rashi:5", "date": DAY, "rating": 1})
    with api.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(HoroscopeFeedback)) == 3
    assert api.delete(f"/v1/profiles/{pid}", headers=alice).status_code == 204   # the profile's feedback goes too
    with api.session_factory() as db:
        assert sorted(f.subject for f in db.scalars(select(HoroscopeFeedback))) == ["rashi:5", "rashi:5"]
    assert api.delete("/v1/me", headers=alice).status_code == 204                # and the account's
    with api.session_factory() as db:
        left = list(db.scalars(select(HoroscopeFeedback)))
        assert len(left) == 1 and left[0].rating == 1   # only bob's remains
        assert db.scalar(select(func.count()).select_from(BirthProfile)) == 0


def test_export_includes_my_feedback_only(api):
    alice, bob = login(api, "alice"), login(api, "bob")
    api.post("/v1/horoscope/feedback", headers=alice, json={"subject": "rashi:5", "date": DAY, "rating": 1,
                                                            "felt_accurate": True})
    api.post("/v1/horoscope/feedback", headers=bob, json={"subject": "rashi:7", "date": DAY, "rating": -1})
    fb = api.get("/v1/me/export", headers=alice).json()["horoscope_feedback"]
    assert [(f["subject"], f["rating"], f["felt_accurate"]) for f in fb] == [("rashi:5", 1, True)]
