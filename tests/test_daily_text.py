from datetime import timedelta

import pytest
from sqlalchemy import func, select

from astrodaily.api.daily_text_routes import get_daily_llm_client
from astrodaily.chat.llm import LlmError, LlmResult
from astrodaily.config import get_settings
from astrodaily.horoscope import service
from astrodaily.main import app
from astrodaily.models import DailyHoroscope, Place


class FakeLlm:
    def __init__(self, *replies, error=None):
        self.replies, self.error, self.calls = list(replies) or ["A steady day. Take one thing at a time."], error, []

    def generate(self, system, turns):
        self.calls.append((system, list(turns)))
        if self.error:
            raise self.error
        text = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        return LlmResult(text=text, tokens_in=100, tokens_out=60, model="fake-model")


@pytest.fixture
def api(client):
    with client.session_factory() as db:
        db.add(Place(id=1273294, name="Delhi", name_hi="दिल्ली", state="Delhi", district="Central Delhi",
                     country_code="IN", latitude=28.65195, longitude=77.23149, population=11034555,
                     timezone="Asia/Kolkata"))
        db.commit()
    yield client
    app.dependency_overrides.pop(get_daily_llm_client, None)
    get_settings.cache_clear()


def use_llm(llm):
    app.dependency_overrides[get_daily_llm_client] = lambda: llm
    return llm


def login(client, sub="alice", consent=True):
    r = client.post("/v1/auth/google", json={"id_token": f"good-{sub}"})
    assert r.status_code == 200, r.text
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    if consent:
        assert client.patch("/v1/me", headers=h, json={"consent_version": "2026-11"}).status_code == 200
    return h


def profile(client, h):
    r = client.post("/v1/profiles", headers=h, json={"label": "SecretLabel", "birth_date": "1990-05-15",
                                                     "birth_time": "10:00", "place_id": 1273294})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def ready(api):
    h = login(api)
    p = profile(api, h)
    return api, h, p


def today():
    return service.today_in("Asia/Kolkata")


def get(api, h, **q):
    return api.get("/v1/me/horoscope/text", headers=h, params=q)


def rows(api):
    with api.session_factory() as db:
        return db.scalar(select(func.count(DailyHoroscope.id)))


def test_requires_login_consent_and_a_profile(api):
    assert api.get("/v1/me/horoscope/text").status_code == 401
    assert get(api, login(api, "nocons", consent=False)).status_code == 403
    assert get(api, login(api, "noprofile")).status_code == 404


def test_built_once_then_saved_for_the_day(ready):
    api, h, _ = ready
    llm = use_llm(FakeLlm("First text.", "Second text."))
    a = get(api, h)
    assert a.status_code == 200, a.text
    body = a.json()
    assert body["text"] == "First text." and body["status"] == "draft" and body["lang"] == "en"
    assert body["date"] == today().isoformat() and body["disclaimer"]["en"]
    b = get(api, h)
    assert b.json()["text"] == "First text."  # the day's horoscope does not change
    assert len(llm.calls) == 1 and rows(api) == 1


def test_each_language_and_day_is_its_own(ready):
    api, h, _ = ready
    llm = use_llm(FakeLlm("English text.", "हिंदी पाठ।", "Tomorrow text."))
    assert get(api, h).json()["text"] == "English text."
    assert get(api, h, lang="hi").json()["text"] == "हिंदी पाठ।"
    assert get(api, h, date=(today() + timedelta(days=1)).isoformat()).json()["text"] == "Tomorrow text."
    assert len(llm.calls) == 3 and rows(api) == 3
    assert "Hindi" in llm.calls[1][0] and "English" in llm.calls[0][0]


def test_only_today_and_tomorrow(ready):
    api, h, _ = ready
    llm = use_llm(FakeLlm())
    for d in (today() - timedelta(days=1), today() + timedelta(days=2)):
        assert get(api, h, date=d.isoformat()).status_code == 422
    assert llm.calls == []


def test_model_unavailable_saves_nothing_and_the_next_open_tries_again(ready):
    api, h, _ = ready
    use_llm(FakeLlm(error=LlmError("network")))
    assert get(api, h).status_code == 503 and rows(api) == 0
    use_llm(FakeLlm("It works now."))
    assert get(api, h).json()["text"] == "It works now."


def test_no_api_key_is_503(ready):
    api, h, _ = ready
    use_llm(None)
    assert get(api, h).status_code == 503 and rows(api) == 0


def test_a_reply_that_breaks_the_tone_rules_is_retried_once_and_never_saved_if_it_keeps_breaking(ready):
    api, h, _ = ready
    llm = use_llm(FakeLlm("You will definitely get rich.", "A calm day for steady work."))
    assert get(api, h).json()["text"] == "A calm day for steady work." and len(llm.calls) == 2
    api2 = login(api, "bob")
    profile(api, api2)
    use_llm(FakeLlm("You will definitely get rich."))
    assert get(api, api2).status_code == 503
    assert rows(api) == 1


def test_free_limit_is_off_by_default_and_can_be_set(ready, monkeypatch):
    api, h, _ = ready
    use_llm(FakeLlm())
    tomorrow = (today() + timedelta(days=1)).isoformat()
    assert get(api, h).status_code == 200 and get(api, h, date=tomorrow).status_code == 200  # no limit
    monkeypatch.setenv("DAILY_HOROSCOPE_FREE_LIMIT", "1")
    get_settings.cache_clear()
    assert get(api, h).status_code == 200  # already written: still shown
    assert get(api, h, lang="hi").status_code == 200  # same day, other language: not a new free day
    h2 = login(api, "bob")
    profile(api, h2)
    assert get(api, h2).status_code == 200
    assert get(api, h2, date=tomorrow).status_code == 402


def test_changing_birth_details_throws_away_what_was_written_from_the_old_ones(ready):
    api, h, p = ready
    llm = use_llm(FakeLlm("Old text.", "New text."))
    assert get(api, h).json()["text"] == "Old text."
    r = api.patch(f"/v1/profiles/{p['id']}", headers=h, json={"birth_time": "11:30"})
    assert r.status_code == 200
    assert rows(api) == 0
    assert get(api, h).json()["text"] == "New text." and len(llm.calls) == 2


def test_changing_only_the_label_keeps_it(ready):
    api, h, p = ready
    use_llm(FakeLlm("Kept."))
    get(api, h)
    assert api.patch(f"/v1/profiles/{p['id']}", headers=h, json={"label": "Me"}).status_code == 200
    assert rows(api) == 1


def test_the_model_gets_derived_facts_and_no_personal_details(ready):
    api, h, _ = ready
    llm = use_llm(FakeLlm())
    get(api, h)
    system = llm.calls[0][0]
    for needle in ("Moon sign (rashi)", "day score", "Panchang:", "Delhi", "90 to 130 words"):
        assert needle in system, needle
    for secret in ("SecretLabel", "alice", "example.com", "1990", "10:00", "28.65", "77.23"):
        assert secret not in system, f"{secret!r} leaked to the model"


def test_it_is_in_the_export_and_goes_with_the_account(ready):
    api, h, _ = ready
    use_llm(FakeLlm("Exported text."))
    get(api, h)
    exp = api.get("/v1/me/export", headers=h).json()
    assert [x["text"] for x in exp["daily_horoscopes"]] == ["Exported text."]
    assert api.delete("/v1/me", headers=h).status_code == 204
    assert rows(api) == 0


def test_one_person_never_sees_anothers(ready):
    api, h, _ = ready
    use_llm(FakeLlm("Alice's text.", "Bob's text."))
    get(api, h)
    h2 = login(api, "bob")
    profile(api, h2)
    assert get(api, h2).json()["text"] == "Bob's text."
    assert get(api, h).json()["text"] == "Alice's text."
