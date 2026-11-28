import time

import jwt
import pytest

from astrodaily.api.daily_text_routes import get_daily_llm_client
from astrodaily.auth.tokens import ALGORITHM, create_access_token, create_widget_token
from astrodaily.config import get_settings
from astrodaily.main import app
from test_daily_text import FakeLlm, api, login, profile, rows, use_llm  # noqa: F401


def wtoken(client, h):
    r = client.post("/v1/me/widget-token", headers=h)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def wcard(client, token, **q):
    return client.get("/v1/widget/card", headers={"Authorization": f"Bearer {token}"}, params=q)


@pytest.fixture
def ready(api):
    h = login(api)
    profile(api, h)
    use_llm(FakeLlm("A steady day. Take one thing at a time."))
    return api, h


def test_a_token_is_issued_to_a_signed_in_person_with_consent(api):
    assert api.post("/v1/me/widget-token").status_code == 401
    assert api.post("/v1/me/widget-token", headers=login(api, "nocons", consent=False)).status_code == 403
    r = api.post("/v1/me/widget-token", headers=login(api))
    assert r.status_code == 200 and r.json()["token"] and r.json()["expires_at"]


def test_the_widget_token_reads_the_card_and_builds_the_paragraph(ready):
    api, h = ready
    r = wcard(api, wtoken(api, h))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["paragraph"] == "A steady day. Take one thing at a time."
    assert 1 <= body["score"] <= 5 and body["date"] and body["sign"]["en"] and body["sign"]["hi"]
    assert body["best_window"]["start"] and body["headline"]
    assert rows(api) == 1


def test_it_is_the_same_paragraph_the_app_shows(ready):
    api, h = ready
    first = wcard(api, wtoken(api, h)).json()["paragraph"]
    assert api.get("/v1/me/horoscope/text", headers=h).json()["text"] == first  # one per day, shared


def test_hindi(ready):
    api, h = ready
    use_llm(FakeLlm("हिंदी पाठ।"))
    assert wcard(api, wtoken(api, h), lang="hi").json()["paragraph"] == "हिंदी पाठ।"


def test_without_the_model_the_card_still_comes_without_a_paragraph(ready):
    api, h = ready
    use_llm(FakeLlm(error=__import__("astrodaily.chat.llm", fromlist=["LlmError"]).LlmError("down")))
    body = wcard(api, wtoken(api, h)).json()
    assert body["paragraph"] is None and body["score"] and body["headline"]


def test_the_two_kinds_of_token_do_not_swap(ready):
    api, h = ready
    tok = wtoken(api, h)
    # a widget token is not a session: it opens nothing else
    for path in ("/v1/me", "/v1/me/horoscope", "/v1/profiles", "/v1/me/horoscope/text"):
        assert api.get(path, headers={"Authorization": f"Bearer {tok}"}).status_code == 401, path
    # a session is not a widget token
    access = h["Authorization"].split()[1]
    assert wcard(api, access).status_code == 401
    assert api.get("/v1/widget/card").status_code == 401
    assert wcard(api, "not-a-token").status_code == 401


def test_an_expired_token_is_refused(ready, monkeypatch):
    api, h = ready
    monkeypatch.setenv("WIDGET_TOKEN_DAYS", "-1")
    get_settings.cache_clear()
    try:
        tok = wtoken(api, h)
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
    assert wcard(api, tok).status_code == 401


def test_signing_out_revokes_earlier_tokens_but_not_later_ones(ready):
    api, h = ready
    old = wtoken(api, h)
    assert wcard(api, old).status_code == 200
    refresh = api.post("/v1/auth/google", json={"id_token": "good-alice"}).json()["refresh_token"]
    assert api.post("/v1/auth/logout", json={"refresh_token": refresh}).status_code == 204
    assert wcard(api, old).status_code == 401
    time.sleep(0.01)
    h2 = login(api)  # signing in again and asking again gives a working token
    assert wcard(api, wtoken(api, h2)).status_code == 200
    assert wcard(api, old).status_code == 401


def test_it_needs_consent_and_a_profile(api):
    h = login(api, "noprofile")
    assert wcard(api, wtoken(api, h)).status_code == 404
    uid = None
    # a token for someone who never consented is refused by the card
    h2 = login(api, "nocons", consent=False)
    from astrodaily.models import User
    from sqlalchemy import select
    with api.session_factory() as db:
        uid = db.scalar(select(User.id).where(User.email == "nocons@example.com"))
    tok, _ = create_widget_token(uid)
    assert wcard(api, tok).status_code == 403
