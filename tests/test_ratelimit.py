import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from astrodaily import ratelimit
from astrodaily.config import Settings, get_settings
from astrodaily.main import app

PARAMS = {"date": "2025-11-05", "lat": 28.6, "lon": 77.2}


@pytest.fixture
def small_limits(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PANCHANG_PER_MINUTE", "3")
    monkeypatch.setenv("RATE_LIMIT_AUTH_PER_MINUTE", "2")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_window_logic_with_fake_clock():
    key = ("t", "1.2.3.4")
    assert ratelimit._check("t", "1.2.3.4", 2, 60, 0.0) is None
    assert ratelimit._check("t", "1.2.3.4", 2, 60, 10.0) is None
    wait = ratelimit._check("t", "1.2.3.4", 2, 60, 20.0)
    assert wait == pytest.approx(40.0)  # first hit (t=0) frees up at t=60
    assert ratelimit._check("t", "1.2.3.4", 2, 60, 61.0) is None  # slot freed
    assert ratelimit._check("t", "9.9.9.9", 2, 60, 20.0) is None  # other client unaffected
    assert ratelimit._check("other", "1.2.3.4", 2, 60, 20.0) is None  # other scope unaffected


def test_panchang_is_limited_with_retry_after(small_limits):
    with TestClient(app) as c:
        for _ in range(3):
            assert c.get("/v1/panchang", params=PARAMS).status_code == 200
        r = c.get("/v1/panchang", params=PARAMS)
        assert r.status_code == 429
        assert 1 <= int(r.headers["retry-after"]) <= 61
        assert "Too many requests" in r.json()["detail"]
        assert c.get("/health").status_code == 200  # health is never limited


def test_auth_is_limited_before_google_is_called(small_limits):
    with TestClient(app) as c:
        codes = [c.post("/v1/auth/refresh", json={"refresh_token": "x"}).status_code for _ in range(4)]
    assert codes[2:] == [429, 429]
    assert codes[:2] != [429, 429]


def test_can_be_disabled(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PANCHANG_PER_MINUTE", "1")
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    get_settings.cache_clear()
    try:
        with TestClient(app) as c:
            assert all(c.get("/v1/panchang", params=PARAMS).status_code == 200 for _ in range(5))
    finally:
        get_settings.cache_clear()


def _request(headers: dict, host="10.0.0.1") -> Request:
    scope = {"type": "http", "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
             "client": (host, 1234)}
    return Request(scope)


def test_client_ip_ignores_forwarded_header_without_proxy():
    s = Settings(app_env="local")
    assert ratelimit.client_ip(_request({"x-forwarded-for": "6.6.6.6"}), s) == "10.0.0.1"


def test_client_ip_uses_proxy_appended_entry_in_production():
    s = Settings(app_env="production")
    assert s.proxy_hops() == 1
    # A client forging "6.6.6.6" cannot change the last entry, which the proxy added.
    assert ratelimit.client_ip(_request({"x-forwarded-for": "6.6.6.6, 203.0.113.7"}), s) == "203.0.113.7"
    assert ratelimit.client_ip(_request({}), s) == "10.0.0.1"


def test_forged_forwarded_header_does_not_dodge_limit(monkeypatch, small_limits):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "x" * 40)
    get_settings.cache_clear()
    with TestClient(app) as c:
        codes = [c.get("/v1/panchang", params=PARAMS,
                       headers={"x-forwarded-for": f"6.6.6.{i}, 203.0.113.7"}).status_code for i in range(5)]
    assert codes[:3] == [200, 200, 200] and codes[3:] == [429, 429]
