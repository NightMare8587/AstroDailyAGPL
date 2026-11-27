import io
import zipfile

import pytest
from sqlalchemy import func, select

from astrodaily.models import Place, PlaceName
from astrodaily.places.normalize import normalize
from astrodaily.tools import import_geonames as ig


def test_normalize():
    assert normalize("Rāvi River") == "ravi river"
    assert normalize("New-Delhi") == "new delhi"
    assert normalize("  St.  John's  ") == "st john s"
    assert normalize("दिल्ली") == "दिल्ली"
    assert normalize("Delhi") == normalize("DELHI") == normalize("dēlhi")


# GeoNames rows: id, name, ascii, alternates, lat, lon, class, code, cc, cc2, a1, a2, a3, a4, pop, elev, dem, tz, date
def row(gid, name, alts="", cls="P", code="PPL", cc="IN", a1="36", a2="", pop="0", tz="Asia/Kolkata", lat="26.8", lon="80.9"):
    return "\t".join([str(gid), name, name, alts, lat, lon, cls, code, cc, "", a1, a2, "", "", pop, "", "", tz, "2020-01-01"])


GEONAMES_ROWS = [
    row(1, "Lucknow", "Lakhnau,Lucknow City", a1="36", a2="123", pop="2817105"),
    row(2, "Ravi River", cls="H", code="STM"),
    row(3, "Lahore", cc="PK", tz="Asia/Karachi"),
    row(4, "Rampur", a1="36", a2="123", pop="5000"),
    row(5, "Rampur", a1="07", pop="900"),
]
ADMIN1 = ["IN.36\tUttar Pradesh\tUttar Pradesh\t1", "IN.07\tDelhi\tDelhi\t2", "PK.01\tPunjab\tPunjab\t3"]
ADMIN2 = ["IN.36.123\tLucknow District\tLucknow District\t9"]
ALT = [  # id, geonameid, lang, name, preferred, short, colloquial, historic
    "10\t1\thi\tलखनऊ\t\t\t\t",
    "11\t1\thi\tलखनउ\t1\t\t\t",
    "12\t1\ten\tLucknow\t1\t\t\t",
    "13\t4\thi\tरामपुर\t\t\t\t1",  # historic: ignored
]


def test_parsers():
    a1 = ig.load_admin_names(ADMIN1, "IN")
    a2 = ig.load_admin_names(ADMIN2, "IN")
    assert a1 == {"IN.36": "Uttar Pradesh", "IN.07": "Delhi"}
    hindi = ig.load_hindi_names(ALT)
    assert hindi == {1: "लखनउ"}  # preferred wins; historic and non-Hindi ignored
    out = list(ig.parse_places(GEONAMES_ROWS, "IN", a1, a2, hindi))
    assert [p["id"] for p, _ in out] == [1, 4, 5]  # river and Pakistan row skipped
    lucknow, names = out[0]
    assert lucknow["state"] == "Uttar Pradesh" and lucknow["district"] == "Lucknow District"
    assert lucknow["name_hi"] == "लखनउ" and lucknow["population"] == 2817105
    assert "lakhnau" in names and "lucknow city" in names and "लखनउ" in names
    assert names.count("lucknow") == 1  # name and ascii name are deduplicated


def _write_data_dir(tmp_path, rows=GEONAMES_ROWS):
    def make_zip(name, member, lines):
        with zipfile.ZipFile(tmp_path / name, "w") as z:
            z.writestr(member, "\n".join(lines) + "\n")
    make_zip("IN.zip", "IN.txt", rows)
    make_zip("alternatenames_IN.zip", "IN.txt", ALT)
    (tmp_path / "admin1CodesASCII.txt").write_text("\n".join(ADMIN1) + "\n", encoding="utf-8")
    (tmp_path / "admin2Codes.txt").write_text("\n".join(ADMIN2) + "\n", encoding="utf-8")
    return tmp_path


def test_import_is_idempotent_and_replaces(engine, tmp_path):
    d = _write_data_dir(tmp_path)
    assert ig.import_country(engine, "IN", d)[0] == 3
    assert ig.import_country(engine, "IN", d)[0] == 3
    from sqlalchemy.orm import Session
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Place)) == 3
        assert db.scalar(select(func.count()).select_from(PlaceName)) == db.scalar(
            select(func.count()).select_from(PlaceName).where(PlaceName.place_id.in_([1, 4, 5])))
    # A smaller later file replaces the old rows rather than adding to them.
    d2 = _write_data_dir(tmp_path, GEONAMES_ROWS[:1])
    assert ig.import_country(engine, "IN", d2)[0] == 1
    with Session(engine) as db:
        assert [p.id for p in db.scalars(select(Place))] == [1]


@pytest.fixture
def seeded(client):
    with client.session_factory() as db:
        db.add_all([
            Place(id=1273294, name="Delhi", name_hi="दिल्ली", state="Delhi", district="Central Delhi",
                  country_code="IN", latitude=28.65195, longitude=77.23149, population=11034555, timezone="Asia/Kolkata"),
            Place(id=1261481, name="New Delhi", name_hi="नई दिल्ली", state="Delhi", district="New Delhi",
                  country_code="IN", latitude=28.62137, longitude=77.2148, population=317797, timezone="Asia/Kolkata"),
            Place(id=1275339, name="Mumbai", name_hi="मुंबई", state="Maharashtra", district="Mumbai",
                  country_code="IN", latitude=19.07283, longitude=72.88261, population=12691836, timezone="Asia/Kolkata"),
            Place(id=2001, name="Rampur", state="Uttar Pradesh", district="Rampur",
                  country_code="IN", latitude=28.8, longitude=79.03, population=325248, timezone="Asia/Kolkata"),
            Place(id=2002, name="Rampur", state="Bihar", district="Gaya",
                  country_code="IN", latitude=24.8, longitude=85.0, population=0, timezone="Asia/Kolkata"),
        ])
        db.flush()
        for pid, names in {1273294: ["delhi", "दिल्ली", "dilli"], 1261481: ["new delhi", "नई दिल्ली"],
                           1275339: ["mumbai", "bombay", "मुंबई"], 2001: ["rampur"], 2002: ["rampur"]}.items():
            db.add_all(PlaceName(place_id=pid, name_norm=n) for n in names)
        db.commit()
    return client


def ids(resp):
    assert resp.status_code == 200, resp.text
    return [r["id"] for r in resp.json()["results"]]


def test_search_orders_by_population_and_handles_aliases(seeded):
    assert ids(seeded.get("/v1/places/search", params={"q": "del"})) == [1273294]
    assert ids(seeded.get("/v1/places/search", params={"q": "New Del"})) == [1261481]
    assert ids(seeded.get("/v1/places/search", params={"q": "BOMBAY"})) == [1275339]  # alternate name, any case
    assert ids(seeded.get("/v1/places/search", params={"q": "दिल्ली"})) == [1273294]  # Hindi
    assert ids(seeded.get("/v1/places/search", params={"q": "ram"})) == [2001, 2002]  # bigger first
    r = seeded.get("/v1/places/search", params={"q": "mum"}).json()
    assert "GeoNames" in r["attribution"] and r["results"][0]["name_hi"] == "मुंबई"
    assert r["results"][0]["timezone"] == "Asia/Kolkata" and r["results"][0]["state"] == "Maharashtra"


def test_search_disambiguates_same_names_with_district(seeded):
    res = seeded.get("/v1/places/search", params={"q": "rampur"}).json()["results"]
    assert [(p["state"], p["district"]) for p in res] == [("Uttar Pradesh", "Rampur"), ("Bihar", "Gaya")]


def test_search_edge_cases(seeded):
    assert ids(seeded.get("/v1/places/search", params={"q": "d"})) == []  # too short
    assert ids(seeded.get("/v1/places/search", params={"q": "  "})) == []
    assert ids(seeded.get("/v1/places/search", params={"q": "%%"})) == []  # wildcards are not special
    assert ids(seeded.get("/v1/places/search", params={"q": "d_lhi"})) == []
    assert ids(seeded.get("/v1/places/search", params={"q": "zzzzz"})) == []
    assert len(ids(seeded.get("/v1/places/search", params={"q": "ram", "limit": 1}))) == 1
    assert seeded.get("/v1/places/search", params={"q": "ram", "limit": 0}).status_code == 422
    assert seeded.get("/v1/places/search", params={"q": "ram", "limit": 21}).status_code == 422
    assert seeded.get("/v1/places/search", params={"q": "x" * 101}).status_code == 422
    assert seeded.get("/v1/places/search").status_code == 422


def test_get_place(seeded):
    r = seeded.get("/v1/places/1275339")
    assert r.status_code == 200 and r.json()["name"] == "Mumbai"
    assert seeded.get("/v1/places/999").status_code == 404
    assert seeded.get("/v1/places/abc").status_code == 422


def test_panchang_by_place_id_matches_lat_lon(seeded):
    by_place = seeded.get("/v1/panchang", params={"date": "2025-11-05", "place_id": 1273294})
    by_coords = seeded.get("/v1/panchang", params={"date": "2025-11-05", "lat": 28.65195, "lon": 77.23149})
    assert by_place.status_code == 200
    a, b = by_place.json(), by_coords.json()
    assert a["place"]["name"] == "Delhi" and b["place"] is None
    assert a["sunrise"] == b["sunrise"] and a["tithi"] == b["tithi"]
    assert a["tithi"]["en"] == "Purnima"


def test_panchang_place_id_errors(seeded):
    d = {"date": "2025-11-05"}
    assert seeded.get("/v1/panchang", params={**d, "place_id": 5}).status_code == 404
    assert seeded.get("/v1/panchang", params={**d, "place_id": 1273294, "lat": 1, "lon": 1}).status_code == 422
    assert seeded.get("/v1/panchang", params=d).status_code == 422
    assert seeded.get("/v1/panchang", params={**d, "lat": 28.6}).status_code == 422
    assert seeded.get("/v1/panchang", params={**d, "place_id": 1273294, "tz": "Mars/Base"}).status_code == 422


def test_panchang_place_id_without_database_is_503(monkeypatch):
    from fastapi.testclient import TestClient
    from astrodaily import db as dbmod
    from astrodaily.config import get_settings
    from astrodaily.main import app
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(get_settings(), "database_url", None)
    dbmod.get_engine.cache_clear()
    dbmod._session_factory.cache_clear()
    app.dependency_overrides.clear()
    r = TestClient(app).get("/v1/panchang", params={"date": "2025-11-05", "place_id": 1})
    assert r.status_code == 503
    assert TestClient(app).get("/v1/panchang", params={"date": "2025-11-05", "lat": 28.6, "lon": 77.2}).status_code == 200
