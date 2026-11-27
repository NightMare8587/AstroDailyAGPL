from fastapi.testclient import TestClient

from astrodaily.main import app

client = TestClient(app)


def test_health_exposes_configured_model(monkeypatch):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["gemini_model"] == "gemini-3.5-flash-lite"


def test_gemini_model_is_configurable(monkeypatch):
    from astrodaily.config import get_settings
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.6-flash")
    get_settings.cache_clear()
    try:
        assert client.get("/health").json()["gemini_model"] == "gemini-3.6-flash"
    finally:
        monkeypatch.delenv("GEMINI_MODEL")
        get_settings.cache_clear()


def test_panchang_delhi():
    r = client.get("/v1/panchang", params={"date": "2025-10-21", "lat": 28.6139, "lon": 77.209})
    assert r.status_code == 200
    body = r.json()
    assert body["tithi"]["en"] == "Amavasya" and body["tithi"]["hi"] == "अमावस्या"
    assert body["vara"]["hi"] == "मंगलवार"
    assert len(body["choghadiya"]) == 16
    assert body["timezone"] == "Asia/Kolkata"
    assert body["sunrise"].endswith("+05:30")


def test_panchang_rejects_bad_input():
    base = {"date": "2025-10-21", "lat": 28.6, "lon": 77.2}
    assert client.get("/v1/panchang", params={**base, "tz": "Mars/Base"}).status_code == 422
    assert client.get("/v1/panchang", params={**base, "lat": 95}).status_code == 422
    assert client.get("/v1/panchang", params={"lat": 28.6, "lon": 77.2}).status_code == 422


def test_panchang_date_range_is_bounded():
    base = {"lat": 28.6, "lon": 77.2}
    assert client.get("/v1/panchang", params={**base, "date": "5000-01-01"}).status_code == 422
    assert client.get("/v1/panchang", params={**base, "date": "1700-01-01"}).status_code == 422
    assert client.get("/v1/panchang", params={**base, "date": "1800-01-01"}).status_code == 200
    assert client.get("/v1/panchang", params={**base, "date": "2200-12-31"}).status_code == 200
