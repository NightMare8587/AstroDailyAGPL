from datetime import date, time, timedelta

import pytest

from astrodaily.calc import moonsign
from astrodaily.models import BirthProfile, Place, User


@pytest.fixture
def api(client):
    with client.session_factory() as db:
        db.add_all([
            Place(id=1273294, name="Delhi", name_hi="दिल्ली", state="Delhi", district="Central Delhi",
                  country_code="IN", latitude=28.65195, longitude=77.23149, population=11034555, timezone="Asia/Kolkata"),
            Place(id=1259229, name="Pune", state="Maharashtra", district="Pune", country_code="IN",
                  latitude=18.51957, longitude=73.85535, population=5049968, timezone="Asia/Kolkata"),
        ])
        db.commit()
    return client


def login(client, sub="alice"):
    r = client.post("/v1/auth/google", json={"id_token": f"good-{sub}"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def agree(client, h):
    assert client.patch("/v1/me", headers=h, json={"consent_version": "2026-11"}).status_code == 200


def find_days():
    """One birth date where the Moon stays in one sign all day, and one where it changes sign."""
    one = two = None
    for i in range(40):
        day = date(1996, 8, 1) + timedelta(days=i)
        c = moonsign.candidate_signs(day, "Asia/Kolkata", None)
        one = one or (day, c)
        two = two or ((day, c) if len(c) == 2 else None)
        if one and two:
            return one, two
    raise AssertionError("no such days found")


# ------------------------------------------------------------------ the engine

def test_a_well_known_chart(api):
    # Narendra Modi, 17 Sep 1950, about 11:00 IST: Moon in Scorpio, Anuradha, pada 2 (his published chart).
    m = moonsign.moon_at_birth(date(1950, 9, 17), time(11, 0), "Asia/Kolkata", None)
    assert (m.sign, m.nakshatra, m.pada) == (8, 17, 2)


def test_candidates_are_one_sign_or_two_consecutive_signs_and_match_the_ends_of_the_day(api):
    twos = 0
    for i in range(80):
        day = date(2001, 3, 1) + timedelta(days=i)
        c = moonsign.candidate_signs(day, "Asia/Kolkata", None)
        assert len(c) in (1, 2)
        if len(c) == 2:
            twos += 1
            assert c[1] == c[0] % 12 + 1  # the Moon only ever moves to the next sign
        assert moonsign.moon_at_birth(day, time(0, 0), "Asia/Kolkata", None).sign == c[0]
        assert moonsign.moon_at_birth(day, time(23, 59, 59), "Asia/Kolkata", None).sign == c[-1]
    assert 20 <= twos <= 50  # about 44% of days (the Moon crosses a sign boundary on a bit under half of them)


# ------------------------------------------------------------------ POST /v1/moon-sign

def test_moon_sign_needs_sign_in(api):
    assert api.post("/v1/moon-sign", json={"birth_date": "1996-08-14", "place_id": 1273294}).status_code == 401


def test_moon_sign_with_a_birth_time(api):
    h = login(api)  # no consent needed: nothing is stored
    r = api.post("/v1/moon-sign", headers=h, json={"birth_date": "1950-09-17", "birth_time": "11:00", "place_id": 1273294})
    assert r.status_code == 200, r.text
    assert r.json() == {"time_known": True, "candidates": [8], "moon_sign": 8, "needs_choice": False,
                        "nakshatra": 17, "pada": 2, "name_hint": None}


def test_moon_sign_without_a_time_is_certain_or_a_choice_of_two(api):
    h = login(api)
    (d1, c1), (d2, c2) = find_days()
    one = api.post("/v1/moon-sign", headers=h, json={"birth_date": d1.isoformat(), "place_id": 1273294}).json()
    assert one["moon_sign"] == c1[0] and one["candidates"] == c1 and one["needs_choice"] is False
    two = api.post("/v1/moon-sign", headers=h, json={"birth_date": d2.isoformat(), "place_id": 1273294}).json()
    assert two["moon_sign"] is None and two["candidates"] == c2 and two["needs_choice"] is True and two["time_known"] is False


def test_the_name_points_to_one_of_the_two_signs(api):
    h = login(api)
    _, (d2, c2) = find_days()
    # find a first name whose syllable belongs to one of the two candidate signs
    from astrodaily.calc import namesyl
    name = next(n for n in ["Asha", "Pulkit", "Chandra", "Hari", "Ravi", "Mohan", "Lata", "Vimal", "Kamal", "Meera",
                            "Nitin", "Yash", "Sunil", "Dev", "Jay", "Gita", "Bharat", "Rohit", "Pooja", "Tina"]
                if namesyl.hint(n, c2))
    expect = namesyl.hint(name, c2)
    r = api.post("/v1/moon-sign", headers=h, json={"birth_date": d2.isoformat(), "place_id": 1273294, "first_name": name}).json()
    assert r["name_hint"] == expect and r["name_hint"]["sign"] in c2
    # the hint never appears with a birth time, or when the day is not ambiguous
    d1 = find_days()[0][0]
    assert api.post("/v1/moon-sign", headers=h, json={"birth_date": d1.isoformat(), "place_id": 1273294, "first_name": name}).json()["name_hint"] is None


def test_moon_sign_rejects_bad_input(api):
    h = login(api)
    assert api.post("/v1/moon-sign", headers=h, json={"birth_date": "1700-01-01", "place_id": 1273294}).status_code == 422
    assert api.post("/v1/moon-sign", headers=h, json={"birth_date": "1996-08-14", "place_id": 42}).status_code == 404  # same as the profile endpoints


# ------------------------------------------------------------------ profiles without a birth time

def test_profile_without_a_time_gets_its_sign_when_the_day_is_certain(api):
    h = login(api); agree(api, h)
    (d1, c1), _ = find_days()
    r = api.post("/v1/profiles", headers=h, json={"label": "Me", "birth_date": d1.isoformat(), "place_id": 1273294})
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["birth_time"] is None and p["time_known"] is False and p["moon_sign"] == c1[0]
    assert p["nakshatra"] is None and p["pada"] is None


def test_profile_without_a_time_on_an_ambiguous_day_needs_a_valid_choice(api):
    h = login(api); agree(api, h)
    _, (d2, c2) = find_days()
    body = {"label": "Me", "birth_date": d2.isoformat(), "place_id": 1273294}
    r = api.post("/v1/profiles", headers=h, json=body)
    assert r.status_code == 422 and r.json()["detail"]["candidates"] == c2
    other = next(s for s in range(1, 13) if s not in c2)
    assert api.post("/v1/profiles", headers=h, json={**body, "moon_sign": other}).status_code == 422
    ok = api.post("/v1/profiles", headers=h, json={**body, "moon_sign": c2[1]})
    assert ok.status_code == 201 and ok.json()["moon_sign"] == c2[1]
    assert api.get("/v1/profiles", headers=h).json()[0]["moon_sign"] == c2[1]


def test_a_birth_time_means_the_sign_is_worked_out_and_a_given_one_is_ignored(api):
    h = login(api); agree(api, h)
    r = api.post("/v1/profiles", headers=h, json={"label": "Me", "birth_date": "1950-09-17", "birth_time": "11:00",
                                                  "place_id": 1273294, "moon_sign": 3})
    p = r.json()
    assert p["time_known"] is True and (p["moon_sign"], p["nakshatra"], p["pada"]) == (8, 17, 2)
    with api.session_factory() as db:
        assert db.query(BirthProfile).one().moon_sign is None  # nothing stored: it is always computed


def test_editing_the_time_in_or_out(api):
    h = login(api); agree(api, h)
    (d1, c1), _ = find_days()
    pid = api.post("/v1/profiles", headers=h, json={"label": "Me", "birth_date": d1.isoformat(), "birth_time": "09:30",
                                                   "place_id": 1273294}).json()["id"]
    gone = api.patch(f"/v1/profiles/{pid}", headers=h, json={"birth_time": None}).json()
    assert gone["time_known"] is False and gone["moon_sign"] == c1[0]
    back = api.patch(f"/v1/profiles/{pid}", headers=h, json={"birth_time": "09:30"}).json()
    assert back["time_known"] is True and back["moon_sign"] is not None and back["nakshatra"] is not None
    # moving an unknown-time profile to an ambiguous date asks for a choice and keeps the old data when refused
    d2, c2 = next((d, c) for d, c in ((date(1996, 8, 1) + timedelta(days=i), moonsign.candidate_signs(date(1996, 8, 1) + timedelta(days=i), "Asia/Kolkata", None))
                                      for i in range(40)) if len(c) == 2 and c1[0] not in c)  # a day the old sign cannot be on
    api.patch(f"/v1/profiles/{pid}", headers=h, json={"birth_time": None})
    r = api.patch(f"/v1/profiles/{pid}", headers=h, json={"birth_date": d2.isoformat()})
    assert r.status_code == 422 and r.json()["detail"]["candidates"] == c2
    assert api.get(f"/v1/profiles/{pid}", headers=h).json()["birth_date"] == d1.isoformat()
    ok = api.patch(f"/v1/profiles/{pid}", headers=h, json={"birth_date": d2.isoformat(), "moon_sign": c2[0]})
    assert ok.status_code == 200 and ok.json()["moon_sign"] == c2[0]
    # an edit that does not change the answer (same sign still possible) keeps the earlier choice
    again = api.patch(f"/v1/profiles/{pid}", headers=h, json={"label": "Mine"})
    assert again.status_code == 200 and again.json()["moon_sign"] == c2[0]


def test_no_full_chart_without_a_birth_time(api):
    h = login(api); agree(api, h)
    (d1, _), _ = find_days()
    pid = api.post("/v1/profiles", headers=h, json={"label": "Me", "birth_date": d1.isoformat(), "place_id": 1273294}).json()["id"]
    r = api.get(f"/v1/profiles/{pid}/kundli", headers=h)
    assert r.status_code == 409 and "birth time is not known" in r.json()["detail"]


def test_the_daily_card_for_an_unknown_time_profile_is_the_moon_sign_card(api):
    h = login(api); agree(api, h)
    (d1, c1), _ = find_days()
    pid = api.post("/v1/profiles", headers=h, json={"label": "Me", "birth_date": d1.isoformat(), "place_id": 1273294}).json()["id"]
    day = "2026-11-28"
    mine = api.get(f"/v1/profiles/{pid}/horoscope?date={day}&place_id=1273294", headers=h)
    assert mine.status_code == 200, mine.text
    same = api.get(f"/v1/horoscope/rashi/{c1[0]}?date={day}&place_id=1273294").json()
    assert mine.json()["score"] == same["score"] and mine.json()["areas"] == same["areas"]
    assert mine.json()["subject"]["type"] == "profile"
    assert api.get(f"/v1/me/horoscope?date={day}&place_id=1273294", headers=h).status_code == 200


def test_the_chat_facts_do_not_invent_a_lagna_or_dasha_without_a_time(api):
    from astrodaily.chat import context
    h = login(api); agree(api, h)
    (d1, c1), _ = find_days()
    api.post("/v1/profiles", headers=h, json={"label": "Me", "birth_date": d1.isoformat(), "place_id": 1273294})
    with api.session_factory() as db:
        user = db.query(User).one()
        text = context.build_context(user, user.profiles[0], date(2026, 11, 28))
    assert "birth time unknown" in text and "do not guess" in text
    assert "ascendant (lagna) " not in text.replace("ascendant and running period", "")
    assert "Vimshottari" not in text


# ------------------------------------------------------------------ POST /v1/me/setup (all at once)

SETUP = {"consent_version": "2026-11", "language": "hi", "first_name": " Asha ", "last_name": "Verma",
         "date_of_birth": "1950-09-17", "gender": "female", "birth_time": "11:00", "birth_place_id": 1259229}


def test_setup_saves_everything_in_one_call(api):
    h = login(api)
    r = api.post("/v1/me/setup", headers=h, json={**SETUP, "home_place_id": 1273294})
    assert r.status_code == 200, r.text
    u = r.json()
    assert u["onboarded"] is True and u["first_name"] == "Asha" and u["gender"] == "female" and u["language"] == "hi"
    assert u["consent_version"] == "2026-11" and u["home_place"]["id"] == 1273294
    profiles = api.get("/v1/profiles", headers=h).json()  # consent was recorded, so this is allowed
    assert len(profiles) == 1
    p = profiles[0]
    assert p["label"] == "Me" and p["birth_date"] == "1950-09-17" and p["birth_time"] == "11:00:00"
    assert p["place_id"] == 1259229 and (p["moon_sign"], p["nakshatra"]) == (8, 17)


def test_setup_again_updates_the_same_profile(api):
    h = login(api)
    api.post("/v1/me/setup", headers=h, json=SETUP)
    r = api.post("/v1/me/setup", headers=h, json={**SETUP, "birth_time": "23:30", "birth_place_id": 1273294})
    assert r.status_code == 200
    profiles = api.get("/v1/profiles", headers=h).json()
    assert len(profiles) == 1 and profiles[0]["birth_time"] == "23:30:00" and profiles[0]["place_id"] == 1273294


def test_setup_needs_consent_the_first_time_only(api):
    h = login(api)
    body = {k: v for k, v in SETUP.items() if k != "consent_version"}
    assert api.post("/v1/me/setup", headers=h, json=body).status_code == 422
    assert api.post("/v1/me/setup", headers=h, json=SETUP).status_code == 200
    assert api.post("/v1/me/setup", headers=h, json=body).status_code == 200  # already agreed


def test_setup_requires_the_details(api):
    h = login(api)
    for drop in ("first_name", "last_name", "date_of_birth", "birth_place_id"):
        assert api.post("/v1/me/setup", headers=h, json={k: v for k, v in SETUP.items() if k != drop}).status_code == 422, drop
    for bad in ({"first_name": "  "}, {"date_of_birth": "2999-01-01"}, {"birth_place_id": 42}, {"gender": "robot"}):
        assert api.post("/v1/me/setup", headers=h, json={**SETUP, **bad}).status_code == 422, bad


def test_setup_without_a_time_certain_day_needs_no_choice(api):
    h = login(api)
    (d1, c1), _ = find_days()
    r = api.post("/v1/me/setup", headers=h, json={**SETUP, "birth_time": None, "date_of_birth": d1.isoformat()})
    assert r.status_code == 200 and r.json()["onboarded"] is True
    p = api.get("/v1/profiles", headers=h).json()[0]
    assert p["time_known"] is False and p["moon_sign"] == c1[0]


def test_setup_is_all_or_nothing(api):
    h = login(api)
    _, (d2, c2) = find_days()
    r = api.post("/v1/me/setup", headers=h, json={**SETUP, "birth_time": None, "date_of_birth": d2.isoformat()})
    assert r.status_code == 422 and r.json()["detail"]["candidates"] == c2
    me = api.get("/v1/me", headers=h).json()
    assert me["onboarded"] is False and me["first_name"] is None and me["consent_version"] is None  # nothing was saved
    assert api.get("/v1/profiles", headers=h).status_code == 403  # and consent was not recorded
    ok = api.post("/v1/me/setup", headers=h, json={**SETUP, "birth_time": None, "date_of_birth": d2.isoformat(), "moon_sign": c2[1]})
    assert ok.status_code == 200
    assert api.get("/v1/profiles", headers=h).json()[0]["moon_sign"] == c2[1]


def test_deleting_the_account_removes_the_profile(api):
    h = login(api)
    api.post("/v1/me/setup", headers=h, json=SETUP)
    assert api.delete("/v1/me", headers=h).status_code == 204
    with api.session_factory() as db:
        assert db.query(BirthProfile).count() == 0


def test_export_lists_a_profile_without_a_time(api):
    h = login(api)
    (d1, c1), _ = find_days()
    api.post("/v1/me/setup", headers=h, json={**SETUP, "birth_time": None, "date_of_birth": d1.isoformat()})
    out = api.get("/v1/me/export", headers=h).json()
    assert out["account"]["onboarded"] is True
    assert out["profiles"][0]["time_known"] is False and out["profiles"][0]["moon_sign"] == c1[0]


# ------------------------------------------------------------------ found in review

def test_a_sign_change_in_the_last_minute_of_the_day_counts(api):
    # On 17 Oct 1986 the Moon is in Pisces at 23:59:00 IST but in Aries by 23:59:59.
    assert moonsign.moon_at_birth(date(1986, 10, 17), time(23, 59, 59), "Asia/Kolkata", None).sign == 1
    assert moonsign.moon_at_birth(date(1986, 10, 17), time(23, 59, 0), "Asia/Kolkata", None).sign == 12
    assert moonsign.candidate_signs(date(1986, 10, 17), "Asia/Kolkata", None) == [12, 1]


def test_candidates_cover_every_second_of_the_day(api):
    import random
    random.seed(3)
    for _ in range(60):
        day = date(1950, 1, 1) + timedelta(days=random.randrange(25000))
        cands = moonsign.candidate_signs(day, "Asia/Kolkata", None)
        for _ in range(8):
            t = time(random.randrange(24), random.randrange(60), random.randrange(60))
            assert moonsign.moon_at_birth(day, t, "Asia/Kolkata", None).sign in cands, (day, t)


def test_a_birth_profile_needs_a_time_or_a_moon_sign(api):
    from sqlalchemy.exc import IntegrityError
    h = login(api)
    agree(api, h)
    with api.session_factory() as db:
        user = db.query(User).one()
        db.add(BirthProfile(user_id=user.id, label="Me", birth_date=date(1990, 1, 1), birth_time=None, moon_sign=None,
                            latitude=28.6, longitude=77.2, timezone="Asia/Kolkata"))
        with pytest.raises(IntegrityError):
            db.commit()


def test_setup_keeps_an_explicit_utc_offset_for_the_same_place_and_drops_it_for_a_new_place(api):
    h = login(api)
    body = {"consent_version": "2026-11", "first_name": "Asha", "last_name": "Verma", "date_of_birth": "1950-09-17",
            "birth_time": "11:00", "birth_place_id": 1259229}
    api.post("/v1/me/setup", headers=h, json=body)
    pid = api.get("/v1/profiles", headers=h).json()[0]["id"]
    assert api.patch(f"/v1/profiles/{pid}", headers=h, json={"utc_offset_minutes": 390}).json()["utc_offset_minutes"] == 390
    api.post("/v1/me/setup", headers=h, json=body)
    assert api.get(f"/v1/profiles/{pid}", headers=h).json()["utc_offset_minutes"] == 390
    api.post("/v1/me/setup", headers=h, json={**body, "birth_place_id": 1273294})
    assert api.get(f"/v1/profiles/{pid}", headers=h).json()["utc_offset_minutes"] is None


def test_the_birth_date_may_be_today_in_india_even_when_the_server_clock_is_a_day_behind(api):
    h = login(api)
    tomorrow_utc = (date.today() + timedelta(days=1)).isoformat()
    body = {"consent_version": "2026-11", "first_name": "Asha", "last_name": "Verma", "date_of_birth": tomorrow_utc,
            "birth_time": "01:00", "birth_place_id": 1273294}
    assert api.post("/v1/me/setup", headers=h, json=body).status_code == 200
    two_days = (date.today() + timedelta(days=2)).isoformat()
    assert api.post("/v1/me/setup", headers=h, json={**body, "date_of_birth": two_days}).status_code == 422


def test_the_personal_card_and_chat_use_the_profile_labelled_me(api):
    h = login(api)
    agree(api, h)
    (d1, _), _ = find_days()
    mom = api.post("/v1/profiles", headers=h, json={"label": "Mom", "birth_date": d1.isoformat(), "place_id": 1273294}).json()
    api.post("/v1/me/setup", headers=h, json={"first_name": "Asha", "last_name": "Verma", "date_of_birth": "1950-09-17",
                                              "birth_time": "11:00", "birth_place_id": 1259229})
    me = next(p for p in api.get("/v1/profiles", headers=h).json() if p["label"] == "Me")
    card = api.get("/v1/me/horoscope?date=2026-11-28", headers=h).json()
    assert card["subject"]["profile_id"] == me["id"] != mom["id"]


def test_setup_refuses_a_ninth_profile_when_the_limit_is_reached(api, monkeypatch):
    from astrodaily.config import get_settings
    monkeypatch.setenv("MAX_PROFILES_PER_USER", "1")
    get_settings.cache_clear()
    try:
        h = login(api)
        agree(api, h)
        (d1, _), _ = find_days()
        api.post("/v1/profiles", headers=h, json={"label": "Mom", "birth_date": d1.isoformat(), "place_id": 1273294})
        r = api.post("/v1/me/setup", headers=h, json={"first_name": "Asha", "last_name": "Verma", "date_of_birth": "1950-09-17",
                                                      "birth_time": "11:00", "birth_place_id": 1259229})
        assert r.status_code == 409
    finally:
        monkeypatch.delenv("MAX_PROFILES_PER_USER")
        get_settings.cache_clear()
