from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from astrodaily.chat.llm import LlmError
from astrodaily.config import get_settings
from astrodaily.horoscope import prebuild
from astrodaily.models import DailyHoroscope, RefreshToken, User
from test_daily_text import FakeLlm, api, get, login, profile, rows, today, use_llm  # noqa: F401


def run(api, llm, **kw):
    return prebuild.run(api.session_factory, llm, **kw)


def make_old(api, sub):
    with api.session_factory() as db:
        user = db.scalar(select(User).where(User.email == f"{sub}@example.com"))
        for t in db.scalars(select(RefreshToken).where(RefreshToken.user_id == user.id)):
            t.created_at = datetime.now(timezone.utc) - timedelta(days=30)
        db.commit()


def test_writes_for_people_who_used_the_app_recently_and_leaves_the_rest_for_on_demand(api):
    for sub in ("recent", "away"):
        profile(api, login(api, sub))
    make_old(api, "away")
    login(api, "noprofile")
    login(api, "nocons", consent=False)
    llm = FakeLlm("Built early.")
    res = run(api, llm)
    assert (res.due, res.built, res.errors, res.stopped) == (1, 1, 0, False)
    assert rows(api) == 1 and len(llm.calls) == 1
    # the person who was away gets theirs when they open the app
    h_away = login(api, "away")
    use_llm(FakeLlm("On demand."))
    assert get(api, h_away).json()["text"] == "On demand."


def test_opening_the_app_afterwards_uses_the_saved_text_with_no_model_call(api):
    h = login(api, "alice")
    profile(api, h)
    run(api, FakeLlm("Ready at 4am."))
    llm = use_llm(FakeLlm("Should not be used."))
    assert get(api, h).json()["text"] == "Ready at 4am." and llm.calls == []


def test_running_twice_writes_nothing_new(api):
    profile(api, login(api, "alice"))
    run(api, FakeLlm("One."))
    llm = FakeLlm("Two.")
    res = run(api, llm)
    assert (res.due, res.built) == (0, 0) and llm.calls == [] and rows(api) == 1


def test_uses_the_persons_language(api):
    h = login(api, "alice")
    profile(api, h)
    assert api.patch("/v1/me", headers=h, json={"language": "hi"}).status_code == 200
    llm = FakeLlm("हिंदी पाठ।")
    run(api, llm)
    assert "Hindi" in llm.calls[0][0]
    with api.session_factory() as db:
        assert db.scalar(select(DailyHoroscope.lang)) == "hi"


def test_dry_run_only_counts(api):
    profile(api, login(api, "alice"))
    llm = FakeLlm()
    res = run(api, llm, dry_run=True)
    assert res.due == 1 and res.built == 0 and llm.calls == [] and rows(api) == 0


def test_stops_after_too_many_failures_and_saves_nothing_for_them(api, monkeypatch):
    for sub in ("a", "b", "c", "d"):
        profile(api, login(api, sub))
    monkeypatch.setenv("DAILY_HOROSCOPE_BUILD_MAX_ERRORS", "2")
    monkeypatch.setenv("DAILY_HOROSCOPE_BUILD_WORKERS", "1")
    get_settings.cache_clear()
    res = run(api, FakeLlm(error=LlmError("quota")))
    assert res.errors == 2 and res.stopped and res.built == 0 and rows(api) == 0


def test_free_limit_people_are_skipped_not_failed(api, monkeypatch):
    h = login(api, "alice")
    profile(api, h)
    use_llm(FakeLlm("Used the free day."))
    get(api, h, date=(today() + timedelta(days=1)).isoformat())  # tomorrow's, already written
    monkeypatch.setenv("DAILY_HOROSCOPE_FREE_LIMIT", "1")
    get_settings.cache_clear()
    res = run(api, FakeLlm("Over the limit."))
    assert (res.due, res.built, res.skipped, res.errors) == (1, 0, 1, 0)
