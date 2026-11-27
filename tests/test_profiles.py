import pytest
from sqlalchemy import func, select

from astrodaily.config import get_settings
from astrodaily.models import BirthProfile, Place


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


BODY = {"label": "Me", "birth_date": "1990-05-15", "birth_time": "10:00", "place_id": 1273294}


def make(api, h, **over):
    r = api.post("/v1/profiles", headers=h, json={**BODY, **over})
    assert r.status_code == 201, r.text
    return r.json()


def test_requires_sign_in_and_consent(api):
    assert api.get("/v1/profiles").status_code == 401
    assert api.post("/v1/profiles", json=BODY).status_code == 401
    h = login(api, consent=False)
    for call in (lambda: api.get("/v1/profiles", headers=h), lambda: api.post("/v1/profiles", headers=h, json=BODY)):
        r = call()
        assert r.status_code == 403 and "Consent required" in r.json()["detail"]
    assert api.patch("/v1/me", headers=h, json={"consent_version": "2026-11"}).status_code == 200
    assert api.post("/v1/profiles", headers=h, json=BODY).status_code == 201


def test_create_stores_a_place_snapshot(api):
    h = login(api)
    p = make(api, h)
    assert p["label"] == "Me" and p["birth_date"] == "1990-05-15" and p["birth_time"] == "10:00:00"
    assert p["place_id"] == 1273294 and p["place_name"] == "Delhi, Central Delhi, Delhi"
    assert p["latitude"] == pytest.approx(28.65195) and p["timezone"] == "Asia/Kolkata"
    by_coords = make(api, h, label="Dad", place_id=None, lat=26.9, lon=75.8, tz="Asia/Kolkata")
    assert by_coords["place_id"] is None and by_coords["place_name"] is None and by_coords["longitude"] == 75.8
    assert [x["label"] for x in api.get("/v1/profiles", headers=h).json()] == ["Me", "Dad"]  # oldest first
    default = api.post("/v1/profiles", headers=h, json={k: v for k, v in BODY.items() if k != "label"})
    assert default.json()["label"] == "Me"


def test_create_validation(api):
    h = login(api)
    post = lambda **o: api.post("/v1/profiles", headers=h, json={**BODY, **o}).status_code
    assert post(place_id=None) == 422                      # no place
    assert post(lat=1, lon=1) == 422                       # place_id and coordinates together
    assert post(place_id=999) == 404
    assert post(place_id=None, lat=26.9, lon=75.8, tz="Mars/Base") == 422
    assert post(birth_date="1700-01-01") == 422 and post(birth_date="2500-01-01") == 422
    assert post(birth_time="25:00") == 422
    assert post(label="") == 422 and post(label="x" * 41) == 422
    assert post(utc_offset_minutes=9999) == 422


def test_profiles_are_private_to_their_owner(api):
    alice, bob = login(api, "alice"), login(api, "bob")
    mine = make(api, alice)
    pid = mine["id"]
    assert api.get("/v1/profiles", headers=bob).json() == []
    for call in (
        lambda: api.get(f"/v1/profiles/{pid}", headers=bob),
        lambda: api.patch(f"/v1/profiles/{pid}", headers=bob, json={"label": "stolen"}),
        lambda: api.delete(f"/v1/profiles/{pid}", headers=bob),
        lambda: api.get(f"/v1/profiles/{pid}/kundli", headers=bob),
    ):
        assert call().status_code == 404   # looks exactly like a profile that does not exist
    assert api.get(f"/v1/profiles/{pid}", headers=alice).json()["label"] == "Me"  # untouched
    assert api.get("/v1/profiles/not-a-uuid", headers=alice).status_code == 422


def test_profile_limit(api, monkeypatch):
    monkeypatch.setenv("MAX_PROFILES_PER_USER", "2")
    get_settings.cache_clear()
    try:
        h = login(api)
        a, _ = make(api, h), make(api, h, label="Mom")
        r = api.post("/v1/profiles", headers=h, json=BODY)
        assert r.status_code == 409
        assert api.delete(f"/v1/profiles/{a['id']}", headers=h).status_code == 204
        assert api.post("/v1/profiles", headers=h, json=BODY).status_code == 201
        # The limit is per user.
        assert api.post("/v1/profiles", headers=login(api, "bob"), json=BODY).status_code == 201
    finally:
        get_settings.cache_clear()


def test_patch_changes_only_what_is_sent(api):
    h = login(api)
    p = make(api, h)
    url = f"/v1/profiles/{p['id']}"
    r = api.patch(url, headers=h, json={"label": "Self"}).json()
    assert r["label"] == "Self" and r["place_name"] == p["place_name"] and r["birth_time"] == "10:00:00"
    r = api.patch(url, headers=h, json={"birth_time": "10:30", "birth_date": "1991-01-02"}).json()
    assert r["birth_time"] == "10:30:00" and r["birth_date"] == "1991-01-02" and r["label"] == "Self"
    r = api.patch(url, headers=h, json={"place_id": 1275339}).json()
    assert r["place_name"] == "Mumbai, Mumbai, Maharashtra" and r["latitude"] == pytest.approx(19.07283)
    r = api.patch(url, headers=h, json={"lat": 26.9, "lon": 75.8}).json()
    assert r["place_id"] is None and r["place_name"] is None and r["latitude"] == 26.9
    assert api.patch(url, headers=h, json={"utc_offset_minutes": 353}).json()["utc_offset_minutes"] == 353
    assert api.patch(url, headers=h, json={"utc_offset_minutes": None}).json()["utc_offset_minutes"] is None
    assert api.patch(url, headers=h, json={"place_id": 999}).status_code == 404
    assert api.patch(url, headers=h, json={"birth_date": "1700-01-01"}).status_code == 422
    assert api.patch(url, headers=h, json={"lat": 5}).status_code == 422   # half a coordinate
    assert api.get(url, headers=h).json()["latitude"] == 26.9               # failed patches changed nothing


def test_profile_kundli_matches_the_stateless_calculation(api):
    h = login(api)
    p = make(api, h)
    saved = api.get(f"/v1/profiles/{p['id']}/kundli", headers=h, params={"as_of": "2026-11-27"})
    assert saved.status_code == 200, saved.text
    direct = api.post("/v1/kundli", json={"date": "1990-05-15", "time": "10:00", "place_id": 1273294,
                                           "as_of": "2026-11-27"}).json()
    s = saved.json()
    assert s["lagna"] == direct["lagna"] and s["planets"] == direct["planets"]
    assert s["dasha"]["current"] == direct["dasha"]["current"] and s["birth"]["place"]["name"] == "Delhi"
    true = api.get(f"/v1/profiles/{p['id']}/kundli", headers=h, params={"node": "true"}).json()
    assert true["node"] == "true"
    assert api.get(f"/v1/profiles/{p['id']}/kundli", headers=h, params={"as_of": "3000-01-01"}).status_code == 422
    # The offset override saved on the profile is used.
    api.patch(f"/v1/profiles/{p['id']}", headers=h, json={"utc_offset_minutes": 353})
    k = api.get(f"/v1/profiles/{p['id']}/kundli", headers=h).json()
    assert k["birth"]["utc_offset_minutes"] == 353


def test_chart_survives_the_place_disappearing(api):
    h = login(api)
    p = make(api, h)
    before = api.get(f"/v1/profiles/{p['id']}/kundli", headers=h, params={"as_of": "2026-11-27"}).json()
    with api.session_factory() as db:
        db.delete(db.get(Place, 1273294))   # e.g. GeoNames dropped it on a re-import
        db.commit()
    got = api.get(f"/v1/profiles/{p['id']}", headers=h).json()
    assert got["place_id"] is None and got["latitude"] == pytest.approx(28.65195) and got["place_name"]
    after = api.get(f"/v1/profiles/{p['id']}/kundli", headers=h, params={"as_of": "2026-11-27"}).json()
    assert after["lagna"] == before["lagna"] and after["planets"] == before["planets"]


def test_export_contains_only_my_data(api):
    alice, bob = login(api, "alice"), login(api, "bob")
    make(api, alice, label="Me")
    make(api, bob, label="Bobs")
    r = api.get("/v1/me/export", headers=alice)
    assert r.status_code == 200
    body = r.json()
    assert body["account"]["email"] == "alice@example.com" and body["consented_at"] is not None
    assert [p["label"] for p in body["profiles"]] == ["Me"]
    assert api.get("/v1/me/export").status_code == 401
    # Export works even before consent: people can always see what is held about them.
    fresh = login(api, "carol", consent=False)
    assert api.get("/v1/me/export", headers=fresh).json()["profiles"] == []


def test_deleting_a_profile_and_the_whole_account(api):
    alice, bob = login(api, "alice"), login(api, "bob")
    a1, a2 = make(api, alice), make(api, alice, label="Mom")
    make(api, bob)
    assert api.delete(f"/v1/profiles/{a1['id']}", headers=alice).status_code == 204
    assert api.get(f"/v1/profiles/{a1['id']}", headers=alice).status_code == 404
    with api.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(BirthProfile)) == 2
    assert api.delete("/v1/me", headers=alice).status_code == 204
    with api.session_factory() as db:
        left = list(db.scalars(select(BirthProfile)))
        assert len(left) == 1 and left[0].label == "Me"   # only Bob's remains
        assert db.scalar(select(func.count()).select_from(Place)) == 2   # places are shared data, untouched
