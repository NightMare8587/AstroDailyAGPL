import json
from datetime import date, datetime, time, timedelta, timezone

import pytest
from sqlalchemy import func, select

from astrodaily.content import catalog as cat
from astrodaily.models import (BirthProfile, DeviceToken, NotificationLog, NotificationPrefs, Place, User)
from astrodaily.notify import dispatch
from astrodaily.notify.message import MAX_BODY, daily_push
from astrodaily.notify.sender import FcmSender, LogSender, Push

IST = timezone(timedelta(hours=5, minutes=30))
TOKEN_A = "token-aaaaaaaaaaaaaaaaaaaaaaaa"
TOKEN_B = "token-bbbbbbbbbbbbbbbbbbbbbbbb"


# ---------------------------------------------------------------- fakes

class FakeSender:
    name = "fake"

    def __init__(self, outcome="ok"):
        self.outcome, self.calls = outcome, []

    def send(self, token, push):
        self.calls.append((token, push))
        return self.outcome(token) if callable(self.outcome) else self.outcome


class FakeResp:
    def __init__(self, status, body=None):
        self.status_code, self._body = status, body

    def json(self):
        if self._body is None:
            raise ValueError
        return self._body


class FakeSession:
    def __init__(self, resp=None, exc=None):
        self.resp, self.exc, self.posts = resp, exc, []

    def post(self, url, headers=None, json=None, timeout=None):
        self.posts.append((url, headers, json))
        if self.exc:
            raise self.exc
        return self.resp


class FakeCreds:
    valid, token = True, "bearer-xyz"


SA = json.dumps({"project_id": "demo-proj", "client_email": "x@y", "private_key": "k"})


def fcm(resp=None, exc=None):
    s = FakeSession(resp, exc)
    return FcmSender(SA, session=s, credentials=FakeCreds()), s


# ---------------------------------------------------------------- message

def card(dos=None, best=None, tz="Asia/Kolkata"):
    return {"date": date(2025, 11, 5), "score": 4, "location": {"timezone": tz},
            "dos": dos if dos is not None else [{"text": "A steady day.", "reason": "engine"}],
            "windows": {"best": best if best is not None else [{
                "start": datetime(2025, 11, 5, 4, 45, tzinfo=timezone.utc),
                "end": datetime(2025, 11, 5, 5, 30, tzinfo=timezone.utc)}]}}


def test_message_uses_library_text_and_local_clock():
    p = daily_push(card(), "en")
    assert p.title == "Your day ahead"
    assert p.body == "A steady day. Best time 10:15-11:00"  # 04:45Z is 10:15 in India
    assert p.data == {"type": "daily", "date": "2025-11-05", "score": "4"}


def test_message_falls_back_to_engine_reason_and_hindi_labels():
    p = daily_push(card(dos=[{"text": None, "reason": "engine words"}]), "hi")
    assert p.body.startswith("engine words शुभ समय ") and p.title == "आपका आज का दिन"


def test_message_without_dos_or_window_still_has_a_body():
    assert daily_push(card(dos=[], best=[]), "en").body == "Your day ahead"


def test_message_is_capped_and_carries_no_birth_details():
    long = daily_push(card(dos=[{"text": "word " * 100, "reason": ""}]), "en")
    assert len(long.body) <= MAX_BODY and long.body.endswith("…")
    assert set(long.data) == {"type", "date", "score"}


# ---------------------------------------------------------------- senders

def test_log_sender_always_succeeds():
    assert LogSender().send("t", Push("a", "b", {})) == "ok"


def test_fcm_ok_request_shape():
    s, sess = fcm(FakeResp(200, {"name": "m"}))
    assert s.send(TOKEN_A, Push("T", "B", {"type": "daily"})) == "ok"
    url, headers, body = sess.posts[0]
    assert url == "https://fcm.googleapis.com/v1/projects/demo-proj/messages:send"
    assert headers["Authorization"] == "Bearer bearer-xyz"
    m = body["message"]
    assert m["token"] == TOKEN_A and m["notification"] == {"title": "T", "body": "B"}
    assert m["data"] == {"type": "daily"}


@pytest.mark.parametrize("resp,expected", [
    (FakeResp(404, {"error": {"status": "NOT_FOUND"}}), "dead_token"),
    (FakeResp(400, {"error": {"status": "INVALID_ARGUMENT", "details": [{"errorCode": "UNREGISTERED"}]}}), "dead_token"),
    (FakeResp(429, {"error": {"status": "RESOURCE_EXHAUSTED"}}), "retry"),
    (FakeResp(503, None), "retry"),
    (FakeResp(400, {"error": {"status": "INVALID_ARGUMENT"}}), "error"),
    (FakeResp(403, None), "error"),
])
def test_fcm_outcomes(resp, expected):
    s, _ = fcm(resp)
    assert s.send(TOKEN_A, Push("T", "B", {})) == expected


def test_fcm_network_failure_is_retry():
    s, _ = fcm(exc=ConnectionError("boom"))
    assert s.send(TOKEN_A, Push("T", "B", {})) == "retry"


# ---------------------------------------------------------------- due time

def mk(db, *, tz="Asia/Kolkata", home=None, daily_time=time(7, 30), enabled=True, consent=True,
       profile=True, device=TOKEN_A, sub="u1", language="en"):
    u = User(google_sub=sub, email=f"{sub}@example.com", language=language,
             consented_at=datetime.now(timezone.utc) if consent else None)
    db.add(u)
    db.flush()
    if home:
        u.home_place = home
    if profile:
        db.add(BirthProfile(user_id=u.id, label="Me", birth_date=date(1990, 5, 15), birth_time=time(10, 0),
                            latitude=28.65, longitude=77.23, timezone=tz, place_name="Delhi"))
    db.add(NotificationPrefs(user_id=u.id, daily_enabled=enabled, daily_time=daily_time))
    if device:
        db.add(DeviceToken(user_id=u.id, token=device, platform="android"))
    db.commit()
    return u


def at(h, m, day=5):
    return datetime(2025, 11, day, h, m, tzinfo=IST).astimezone(timezone.utc)


@pytest.fixture
def db(engine):
    from sqlalchemy.orm import Session
    with Session(engine) as s:
        yield s


def test_due_window_boundaries(db):
    u = mk(db)
    p, pr = u.notification_prefs, u.profiles[0]
    late = timedelta(minutes=180)
    f = lambda now: dispatch.due_local_date(u, p, pr, now, late)
    assert f(at(7, 29)) is None
    assert f(at(7, 30)) == date(2025, 11, 5)
    assert f(at(10, 30)) == date(2025, 11, 5)
    assert f(at(10, 31)) is None


def test_due_uses_home_city_timezone_over_birth_timezone(db):
    home = Place(id=1, name="London", country_code="GB", latitude=51.5, longitude=-0.12, population=1,
                 timezone="Europe/London")
    db.add(home)
    u = mk(db, home=home)
    when = datetime(2025, 11, 5, 7, 30, tzinfo=timezone.utc)  # 07:30 in London, 13:00 in India
    assert dispatch.due_local_date(u, u.notification_prefs, u.profiles[0], when, timedelta(minutes=5)) == date(2025, 11, 5)
    assert dispatch.due_local_date(u, u.notification_prefs, u.profiles[0], at(7, 30), timedelta(minutes=5)) is None


# ---------------------------------------------------------------- run_once

def run(db, sender, now, **kw):
    return dispatch.run_once(db, sender, cat.EMPTY, now=now, **kw)


def test_sends_once_per_day(db):
    mk(db)
    s = FakeSender()
    r = run(db, s, at(7, 35))
    assert (r.sent, r.failed) == (1, 0) and len(s.calls) == 1
    token, push = s.calls[0]
    assert token == TOKEN_A and push.data["date"] == "2025-11-05" and push.body
    for minute in (40, 45):  # later runs the same morning send nothing
        assert run(db, s, at(7, minute)).sent == 0
    assert len(s.calls) == 1
    assert db.scalar(select(NotificationLog.status)) == "sent"
    # the next local day is a new message
    assert run(db, s, at(7, 35, day=6)).sent == 1 and len(s.calls) == 2


def test_not_sent_before_time_or_too_late(db):
    mk(db)
    s = FakeSender()
    assert run(db, s, at(7, 0)).sent == 0
    assert run(db, s, at(12, 0)).sent == 0
    assert not s.calls and db.scalar(select(func.count(NotificationLog.id))) == 0


@pytest.mark.parametrize("kw", [
    {"enabled": False}, {"consent": False}, {"profile": False}, {"device": None},
])
def test_skips_users_who_cannot_or_should_not_be_messaged(db, kw):
    mk(db, **kw)
    s = FakeSender()
    assert run(db, s, at(7, 35)).sent == 0 and not s.calls
    assert db.scalar(select(func.count(NotificationLog.id))) == 0


def test_disabled_device_is_not_used(db):
    u = mk(db)
    u.devices[0].disabled_at = datetime.now(timezone.utc)
    db.commit()
    s = FakeSender()
    assert run(db, s, at(7, 35)).sent == 0 and not s.calls


def test_sends_to_every_device_and_one_ok_counts(db):
    u = mk(db)
    db.add(DeviceToken(user_id=u.id, token=TOKEN_B, platform="ios"))
    db.commit()
    s = FakeSender(lambda t: "ok" if t == TOKEN_B else "retry")
    r = run(db, s, at(7, 35))
    assert len(s.calls) == 2 and r.sent == 1


def test_dead_token_is_disabled_and_not_retried(db):
    mk(db)
    s = FakeSender("dead_token")
    r = run(db, s, at(7, 35))
    assert r.failed == 1 and r.devices_disabled == 1
    assert db.scalar(select(DeviceToken.disabled_at)) is not None
    assert run(db, s, at(7, 40)).sent == 0 and len(s.calls) == 1  # no active device left


def test_failures_retry_up_to_three_attempts(db):
    mk(db)
    s = FakeSender("retry")
    for i, minute in enumerate((35, 40, 45, 50, 55)):
        run(db, s, at(7, minute))
    assert len(s.calls) == 3
    row = db.scalar(select(NotificationLog))
    assert (row.status, row.attempts) == ("failed", 3)


def test_retry_then_success(db):
    mk(db)
    flaky = FakeSender("retry")
    run(db, flaky, at(7, 35))
    ok = FakeSender("ok")
    r = run(db, ok, at(7, 40))
    assert r.sent == 1 and db.scalar(select(NotificationLog.status)) == "sent"
    assert db.scalar(select(NotificationLog.attempts)) == 2


def test_already_claimed_day_is_skipped(db):
    u = mk(db)
    db.add(NotificationLog(user_id=u.id, kind="daily", local_date=date(2025, 11, 5), status="sending", attempts=1))
    db.commit()
    s = FakeSender()
    assert run(db, s, at(7, 35)).sent == 0 and not s.calls


def test_one_broken_user_does_not_stop_the_run(db, monkeypatch):
    mk(db, sub="u1", device=TOKEN_A)
    mk(db, sub="u2", device=TOKEN_B)
    real = dispatch.daily_push
    n = {"i": 0}

    def flaky(card, lang, **kw):
        n["i"] += 1
        if n["i"] == 1:
            raise RuntimeError("bad card")
        return real(card, lang)

    monkeypatch.setattr(dispatch, "daily_push", flaky)
    s = FakeSender()
    r = run(db, s, at(7, 35))
    assert (r.sent, r.failed) == (1, 1) and r.errors == ["RuntimeError"]


def test_dry_run_writes_and_sends_nothing(db):
    mk(db)
    s = FakeSender()
    r = run(db, s, at(7, 35), dry_run=True)
    assert r.sent == 1 and not s.calls
    assert db.scalar(select(func.count(NotificationLog.id))) == 0
    assert run(db, s, at(7, 35)).sent == 1  # the real run still goes out


def test_uses_user_language_and_library_wording(db):
    mk(db, language="hi")
    rows = [("nakshatra_" + c, "hi", 1, "{nakshatra} परीक्षण पंक्ति", "reviewed", "t")
            for c in ("dhruva", "chara", "kshipra", "mridu", "ugra", "tikshna", "mishra")]
    s = FakeSender()
    dispatch.run_once(db, s, cat.Catalog(rows), now=at(7, 35))
    assert s.calls[0][1].title == "आपका आज का दिन"


# ---------------------------------------------------------------- API

def login(client, sub="alice", consent=True):
    r = client.post("/v1/auth/google", json={"id_token": f"good-{sub}"})
    assert r.status_code == 200, r.text
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    if consent:
        assert client.patch("/v1/me", headers=h, json={"consent_version": "2026-11"}).status_code == 200
    return h


def test_api_requires_login_and_consent(client):
    assert client.get("/v1/me/notifications").status_code == 401
    assert client.post("/v1/me/devices", json={"token": TOKEN_A, "platform": "android"}).status_code == 401
    h = login(client, consent=False)
    assert client.get("/v1/me/notifications", headers=h).status_code == 200  # reading is fine
    assert client.put("/v1/me/notifications", headers=h, json={"daily_enabled": True}).status_code == 403
    assert client.post("/v1/me/devices", headers=h, json={"token": TOKEN_A, "platform": "android"}).status_code == 403


def test_api_defaults_are_off(client):
    h = login(client)
    d = client.get("/v1/me/notifications", headers=h).json()
    assert d["daily_enabled"] is False and d["daily_time"] == "07:30:00" and d["devices"] == []
    assert d["ready_to_send"] is False


def test_api_set_prefs_and_register_device(client):
    h = login(client)
    assert client.put("/v1/me/notifications", headers=h,
                      json={"daily_enabled": True, "daily_time": "06:45"}).json()["daily_time"] == "06:45:00"
    dev = client.post("/v1/me/devices", headers=h, json={"token": TOKEN_A, "platform": "android"})
    assert dev.status_code == 201 and dev.json()["active"] is True
    again = client.post("/v1/me/devices", headers=h, json={"token": TOKEN_A, "platform": "android"})
    assert again.json()["id"] == dev.json()["id"]  # same token, same device
    d = client.get("/v1/me/notifications", headers=h).json()
    assert d["daily_enabled"] is True and len(d["devices"]) == 1
    assert d["ready_to_send"] is False  # no birth profile yet
    assert "token" not in json.dumps(d)  # tokens never come back out


def test_api_transit_alert_switch_is_off_by_default_and_separate_from_the_daily_one(client):
    h = login(client)
    assert client.get("/v1/me/notifications", headers=h).json()["transit_enabled"] is False
    d = client.put("/v1/me/notifications", headers=h, json={"transit_enabled": True}).json()
    assert d["transit_enabled"] is True and d["daily_enabled"] is False
    d = client.put("/v1/me/notifications", headers=h, json={"daily_enabled": True}).json()
    assert d["transit_enabled"] is True  # changing one switch leaves the other alone
    assert client.get("/v1/me/export", headers=h).json()["notifications"]["transit_enabled"] is True


def test_api_rejects_bad_input(client):
    h = login(client)
    assert client.post("/v1/me/devices", headers=h, json={"token": "short", "platform": "android"}).status_code == 422
    assert client.post("/v1/me/devices", headers=h, json={"token": TOKEN_A, "platform": "fax"}).status_code == 422
    assert client.put("/v1/me/notifications", headers=h, json={"daily_time": "25:99"}).status_code == 422


def test_api_device_cap(client):
    h = login(client)
    for i in range(10):
        assert client.post("/v1/me/devices", headers=h,
                           json={"token": f"token-{i:02d}" + "x" * 20, "platform": "android"}).status_code == 201
    assert client.post("/v1/me/devices", headers=h,
                       json={"token": "token-extra" + "x" * 20, "platform": "android"}).status_code == 409


def test_api_token_moves_to_the_newest_account_and_other_user_cannot_delete(client):
    a, b = login(client, "alice"), login(client, "bob")
    dev = client.post("/v1/me/devices", headers=a, json={"token": TOKEN_A, "platform": "ios"}).json()
    # bob cannot see or remove alice's device
    assert client.delete(f"/v1/me/devices/{dev['id']}", headers=b).status_code == 404
    assert len(client.get("/v1/me/notifications", headers=a).json()["devices"]) == 1
    # the phone changes hands: bob registers the same token
    client.post("/v1/me/devices", headers=b, json={"token": TOKEN_A, "platform": "ios"})
    assert client.get("/v1/me/notifications", headers=a).json()["devices"] == []
    assert len(client.get("/v1/me/notifications", headers=b).json()["devices"]) == 1
    assert client.delete(f"/v1/me/devices/{dev['id']}", headers=b).status_code == 204
    assert client.get("/v1/me/notifications", headers=b).json()["devices"] == []


def test_api_export_omits_tokens_and_delete_account_removes_everything(client):
    h = login(client)
    client.put("/v1/me/notifications", headers=h, json={"daily_enabled": True})
    client.post("/v1/me/devices", headers=h, json={"token": TOKEN_A, "platform": "web"})
    exp = client.get("/v1/me/export", headers=h)
    assert exp.status_code == 200 and TOKEN_A not in exp.text
    n = exp.json()["notifications"]
    assert n["daily_enabled"] is True and n["devices"][0]["platform"] == "web"
    assert client.delete("/v1/me", headers=h).status_code == 204
    with client.session_factory() as db:
        for model in (DeviceToken, NotificationPrefs, NotificationLog):
            assert db.scalar(select(func.count()).select_from(model)) == 0


def test_a_profile_without_a_birth_time_still_gets_the_daily_message(db):
    u = mk(db, profile=False)
    db.add(BirthProfile(user_id=u.id, label="Me", birth_date=date(1990, 5, 15), birth_time=None, moon_sign=4,
                        latitude=28.65, longitude=77.23, timezone="Asia/Kolkata", place_name="Delhi"))
    db.commit()
    s = FakeSender()
    r = run(db, s, at(7, 35))
    assert (r.sent, r.failed) == (1, 0) and s.calls[0][1].body


def test_the_message_uses_the_profile_labelled_me_not_a_family_member(db):
    u = mk(db, profile=False)
    db.add(BirthProfile(user_id=u.id, label="Mom", birth_date=date(1960, 1, 1), birth_time=None, moon_sign=1,
                        latitude=19.07, longitude=72.88, timezone="Asia/Kolkata", place_name="Mumbai"))
    db.flush()
    db.add(BirthProfile(user_id=u.id, label="Me", birth_date=date(1990, 5, 15), birth_time=None, moon_sign=9,
                        latitude=28.65, longitude=77.23, timezone="Asia/Kolkata", place_name="Delhi"))
    db.commit()
    from astrodaily.models import primary_profile
    assert primary_profile(db.get(User, u.id)).moon_sign == 9
