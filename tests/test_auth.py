from datetime import timedelta

import jwt
import pytest
from sqlalchemy import func, select

from astrodaily.auth import tokens
from astrodaily.config import get_settings
from astrodaily.db import normalize_database_url
from astrodaily.models import RefreshToken, User, utcnow


def login(client, sub="alice"):
    r = client.post("/v1/auth/google", json={"id_token": f"good-{sub}"})
    assert r.status_code == 200, r.text
    return r.json()


def auth(tok):
    return {"Authorization": f"Bearer {tok['access_token']}"}


def test_login_creates_user_and_is_idempotent(client):
    first = login(client)
    second = login(client)
    assert first["user"]["id"] == second["user"]["id"]
    assert first["user"]["email"] == "alice@example.com" and first["user"]["language"] == "en"
    assert first["token_type"] == "bearer" and first["expires_in"] == 900
    with client.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 1


def test_bad_google_token_is_rejected(client):
    assert client.post("/v1/auth/google", json={"id_token": "nope"}).status_code == 401


def test_me_requires_valid_token(client):
    assert client.get("/v1/me").status_code == 401
    assert client.get("/v1/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
    tok = login(client)
    r = client.get("/v1/me", headers=auth(tok))
    assert r.status_code == 200 and r.json()["email"] == "alice@example.com"


def test_expired_and_wrong_type_tokens_rejected(client):
    tok = login(client)
    secret = get_settings().require_jwt_secret()
    now = utcnow()
    expired = jwt.encode({"sub": tok["user"]["id"], "typ": "access", "iat": now - timedelta(hours=2),
                          "exp": now - timedelta(hours=1)}, secret, algorithm="HS256")
    wrong = jwt.encode({"sub": tok["user"]["id"], "typ": "refresh", "iat": now,
                        "exp": now + timedelta(hours=1)}, secret, algorithm="HS256")
    forged = jwt.encode({"sub": tok["user"]["id"], "typ": "access", "iat": now,
                         "exp": now + timedelta(hours=1)}, "another-secret-another-secret-12345", algorithm="HS256")
    for bad in (expired, wrong, forged):
        assert client.get("/v1/me", headers={"Authorization": f"Bearer {bad}"}).status_code == 401


def test_update_language_and_consent(client):
    tok = login(client)
    r = client.patch("/v1/me", headers=auth(tok), json={"language": "hi", "consent_version": "2026-11"})
    assert r.status_code == 200
    assert r.json()["language"] == "hi" and r.json()["consent_version"] == "2026-11"
    with client.session_factory() as db:
        assert db.scalar(select(User)).consented_at is not None
    assert client.patch("/v1/me", headers=auth(tok), json={"language": "fr"}).status_code == 422


def test_refresh_rotates_and_reuse_revokes_everything(client):
    tok = login(client)
    rotated = client.post("/v1/auth/refresh", json={"refresh_token": tok["refresh_token"]})
    assert rotated.status_code == 200
    new = rotated.json()
    assert new["refresh_token"] != tok["refresh_token"]
    assert client.get("/v1/me", headers=auth(new)).status_code == 200
    # Replaying the old token fails and burns the new one too.
    assert client.post("/v1/auth/refresh", json={"refresh_token": tok["refresh_token"]}).status_code == 401
    assert client.post("/v1/auth/refresh", json={"refresh_token": new["refresh_token"]}).status_code == 401


def test_refresh_unknown_and_expired(client):
    assert client.post("/v1/auth/refresh", json={"refresh_token": "unknown"}).status_code == 401
    tok = login(client)
    with client.session_factory() as db:
        row = db.scalar(select(RefreshToken))
        row.expires_at = utcnow() - timedelta(days=1)
        db.commit()
    assert client.post("/v1/auth/refresh", json={"refresh_token": tok["refresh_token"]}).status_code == 401


def test_logout_revokes_refresh_token(client):
    tok = login(client)
    assert client.post("/v1/auth/logout", json={"refresh_token": tok["refresh_token"]}).status_code == 204
    assert client.post("/v1/auth/refresh", json={"refresh_token": tok["refresh_token"]}).status_code == 401
    # Logging out with an unknown token is harmless.
    assert client.post("/v1/auth/logout", json={"refresh_token": "unknown"}).status_code == 204


def test_refresh_tokens_are_stored_hashed(client):
    tok = login(client)
    with client.session_factory() as db:
        row = db.scalar(select(RefreshToken))
        assert row.token_hash != tok["refresh_token"] and len(row.token_hash) == 64


def test_delete_account_removes_user_and_tokens(client):
    alice = login(client, "alice")
    bob = login(client, "bob")
    assert client.delete("/v1/me", headers=auth(alice)).status_code == 204
    assert client.get("/v1/me", headers=auth(alice)).status_code == 401
    assert client.post("/v1/auth/refresh", json={"refresh_token": alice["refresh_token"]}).status_code == 401
    with client.session_factory() as db:
        assert [u.google_sub for u in db.scalars(select(User))] == ["bob"]
        assert db.scalar(select(func.count()).select_from(RefreshToken)) == 1
    assert client.get("/v1/me", headers=auth(bob)).status_code == 200


def test_real_google_verifier_paths(monkeypatch):
    from fastapi import HTTPException
    from astrodaily.auth import google as g

    monkeypatch.setenv("GOOGLE_CLIENT_IDS", "")
    get_settings.cache_clear()
    with pytest.raises(HTTPException) as e:
        g.verify_google_token("x")
    assert e.value.status_code == 503

    monkeypatch.setenv("GOOGLE_CLIENT_IDS", "web-id.apps.googleusercontent.com, android-id")
    get_settings.cache_clear()
    assert get_settings().google_client_id_list == ["web-id.apps.googleusercontent.com", "android-id"]
    with pytest.raises(HTTPException) as e:  # malformed token, rejected before any network call
        g.verify_google_token("not.a.jwt")
    assert e.value.status_code == 401

    seen = {}

    def fake_verify(token, request, audience=None):
        seen["audience"] = audience
        return {"sub": "1", "email": "a@b.c", "email_verified": False}

    monkeypatch.setattr(g.google_id_token, "verify_oauth2_token", fake_verify)
    with pytest.raises(HTTPException) as e:
        g.verify_google_token("t")
    assert e.value.status_code == 401 and seen["audience"] == ["web-id.apps.googleusercontent.com", "android-id"]
    get_settings.cache_clear()


def test_jwt_secret_required_outside_local(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError):
            tokens.create_access_token(__import__("uuid").uuid4())
    finally:
        get_settings.cache_clear()


def test_database_url_normalisation():
    assert normalize_database_url("postgres://u:p@h/d") == "postgresql+psycopg://u:p@h/d"
    assert normalize_database_url("postgresql://u:p@h/d") == "postgresql+psycopg://u:p@h/d"
    assert normalize_database_url("postgresql+psycopg://u:p@h/d") == "postgresql+psycopg://u:p@h/d"


def test_db_endpoints_503_without_database(monkeypatch):
    from fastapi.testclient import TestClient
    from astrodaily import db as dbmod
    from astrodaily.main import app

    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    dbmod.get_engine.cache_clear()
    dbmod._session_factory.cache_clear()
    monkeypatch.setattr(get_settings(), "database_url", None)
    with TestClient(app) as c:
        assert c.post("/v1/auth/refresh", json={"refresh_token": "x"}).status_code == 503


# ---- setup page fields: first name, last name, date of birth, gender

def test_new_account_is_not_onboarded(client):
    u = login(client)["user"]
    assert u["onboarded"] is False
    assert u["first_name"] is None and u["last_name"] is None and u["date_of_birth"] is None and u["gender"] is None


def test_setup_fields_are_saved_but_the_account_is_onboarded_only_with_a_birth_profile(client):
    tok = login(client)
    r = client.patch("/v1/me", headers=auth(tok), json={"first_name": "  Pulkit ", "last_name": "Sharma  Rao",
                                                        "date_of_birth": "1996-08-14", "gender": "male"})
    assert r.status_code == 200, r.text
    u = r.json()
    assert u["first_name"] == "Pulkit" and u["last_name"] == "Sharma Rao"  # trimmed, inner spaces collapsed
    assert u["date_of_birth"] == "1996-08-14" and u["gender"] == "male"
    assert u["onboarded"] is False  # onboarding also needs the "Me" birth profile (POST /v1/me/setup)


def test_gender_is_optional_and_can_be_cleared(client):
    tok = login(client)
    assert client.patch("/v1/me", headers=auth(tok), json={"gender": "female"}).json()["gender"] == "female"
    assert client.patch("/v1/me", headers=auth(tok), json={"gender": None}).json()["gender"] is None


@pytest.mark.parametrize("body", [
    {"first_name": "   "},
    {"last_name": ""},
    {"first_name": "x" * 41},
    {"date_of_birth": "2999-01-01"},
    {"date_of_birth": "1899-12-31"},
    {"date_of_birth": "not-a-date"},
    {"gender": "robot"},
])
def test_setup_fields_reject_bad_values(client, body):
    tok = login(client)
    assert client.patch("/v1/me", headers=auth(tok), json=body).status_code == 422


def test_names_and_birth_date_cannot_be_cleared_but_gender_can(client):
    tok = login(client)
    client.patch("/v1/me", headers=auth(tok), json={"first_name": "Asha", "last_name": "Verma",
                                                    "date_of_birth": "1990-01-02", "gender": "female"})
    u = client.patch("/v1/me", headers=auth(tok), json={"first_name": None, "date_of_birth": None, "gender": None}).json()
    assert u["first_name"] == "Asha" and u["date_of_birth"] == "1990-01-02"  # null leaves them as they were
    assert u["gender"] is None  # an explicit null clears the optional field
    u = client.patch("/v1/me", headers=auth(tok), json={"language": "hi"}).json()
    assert u["language"] == "hi" and u["first_name"] == "Asha"  # leaving a field out keeps it


def test_export_includes_setup_fields(client):
    tok = login(client)
    client.patch("/v1/me", headers=auth(tok), json={"first_name": "Asha", "last_name": "Verma", "date_of_birth": "1990-01-02"})
    acct = client.get("/v1/me/export", headers=auth(tok)).json()["account"]
    assert acct["first_name"] == "Asha" and acct["date_of_birth"] == "1990-01-02"
