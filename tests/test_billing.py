"""Plans, buying with the fake store, and what a free account does not get."""
from datetime import date, timedelta, timezone, datetime

import pytest

from astrodaily.billing import service
from astrodaily.billing.verify import FakeVerifier, InvalidPurchase
from astrodaily.config import get_settings
from astrodaily.horoscope import service as horoscope
from astrodaily.models import Place, Subscription, User
from test_daily_text import login, profile  # the signed-in user and birth profile helpers

TOKEN = "fake:monthly:paid:abc12345"


@pytest.fixture
def api(client):
    with client.session_factory() as db:
        db.add(Place(id=1273294, name="Delhi", name_hi="दिल्ली", state="Delhi", district="Central Delhi",
                     country_code="IN", latitude=28.65195, longitude=77.23149, population=11034555,
                     timezone="Asia/Kolkata"))
        db.commit()
    return client


@pytest.fixture
def paywall(monkeypatch):
    """The real free limits (the other tests run with everything free)."""
    monkeypatch.setenv("DAILY_HOROSCOPE_REQUIRES_PREMIUM", "true")
    monkeypatch.setenv("CHAT_FREE_DAILY_MESSAGE_LIMIT", "5")
    monkeypatch.setenv("FREE_CALENDAR_DAYS_AHEAD", "1")
    get_settings.cache_clear()


@pytest.fixture
def fake_store(monkeypatch):
    monkeypatch.setenv("BILLING_PROVIDER", "fake")
    get_settings.cache_clear()


def buy(api, h, product="monthly", token=TOKEN):
    return api.post("/v1/me/subscription", headers=h, json={"product_id": product, "purchase_token": token})


def today():
    return horoscope.today_in("Asia/Kolkata")


# ---------------------------------------------------------------- plans and buying

def test_plans_are_public_and_say_which_store_is_on(api):
    r = api.get("/v1/plans")
    assert r.status_code == 200 and r.json()["provider"] == "none"
    assert {p["id"]: (p["price_inr"], p["trial_days"]) for p in r.json()["plans"]} == {"monthly": (49, 7), "yearly": (399, 7)}


def test_nothing_can_be_bought_without_a_store(api):
    h = login(api)
    assert buy(api, h).status_code == 503
    assert api.get("/v1/me/subscription", headers=h).json() == {
        "premium": False, "plan": None, "expires_at": None, "auto_renewing": False, "trial": False, "provider": "none"}
    assert api.post("/v1/me/subscription/fake/cancel", headers=h).status_code == 404  # test-only calls do not exist
    assert api.post("/v1/me/subscription/fake/expire", headers=h).status_code == 404


def test_buying_needs_login(api, fake_store):
    assert api.get("/v1/me/subscription").status_code == 401
    assert api.post("/v1/me/subscription", json={"product_id": "monthly", "purchase_token": TOKEN}).status_code == 401


def test_a_fake_purchase_makes_the_account_premium_until_it_expires(api, fake_store):
    h = login(api)
    r = buy(api, h)
    assert r.status_code == 200
    d = r.json()
    assert d["premium"] and d["plan"] == "monthly" and d["auto_renewing"] and not d["trial"] and d["provider"] == "fake"
    left = datetime.fromisoformat(d["expires_at"]) - datetime.now(timezone.utc)
    assert timedelta(days=29) < left <= timedelta(days=30)
    assert api.get("/v1/me/subscription", headers=h).json()["premium"] is True
    assert buy(api, h).json()["premium"]  # the same token again is not a second purchase
    with api.session_factory() as db:
        assert db.query(Subscription).count() == 1


def test_a_trial_lasts_seven_days_and_yearly_a_year(api, fake_store):
    h = login(api)
    d = buy(api, h, "monthly", "fake:monthly:trial:t1111111").json()
    assert d["trial"] and (datetime.fromisoformat(d["expires_at"]) - datetime.now(timezone.utc)) < timedelta(days=7, seconds=5)
    h2 = login(api, "bob")
    y = buy(api, h2, "yearly", "fake:yearly:paid:y1111111").json()
    assert (datetime.fromisoformat(y["expires_at"]) - datetime.now(timezone.utc)) > timedelta(days=364)


@pytest.mark.parametrize("product,token", [
    ("monthly", "not-a-store-token"), ("monthly", "fake:yearly:paid:abc12345"), ("monthly", "fake:monthly:free:abc12345"),
    ("monthly", "real:monthly:paid:abc12345"),
])
def test_a_purchase_the_store_does_not_know_is_refused(api, fake_store, product, token):
    h = login(api)
    assert buy(api, h, product, token).status_code == 422
    assert api.get("/v1/me/subscription", headers=h).json()["premium"] is False


def test_unknown_plan_and_short_token_are_rejected(api, fake_store):
    h = login(api)
    assert api.post("/v1/me/subscription", headers=h, json={"product_id": "lifetime", "purchase_token": TOKEN}).status_code == 422
    assert api.post("/v1/me/subscription", headers=h, json={"product_id": "monthly", "purchase_token": "x"}).status_code == 422


def test_a_token_cannot_be_shared_between_accounts(api, fake_store):
    assert buy(api, login(api, "alice")).status_code == 200
    h2 = login(api, "bob")
    assert buy(api, h2).status_code == 409
    assert api.get("/v1/me/subscription", headers=h2).json()["premium"] is False


def test_cancelling_keeps_access_to_the_end_of_the_period(api, fake_store):
    h = login(api)
    buy(api, h)
    d = api.post("/v1/me/subscription/fake/cancel", headers=h).json()
    assert d["premium"] is True and d["auto_renewing"] is False and d["expires_at"]


def test_cancel_without_a_subscription_is_a_404(api, fake_store):
    assert api.post("/v1/me/subscription/fake/cancel", headers=login(api)).status_code == 404


def test_expiry_ends_premium(api, fake_store):
    h = login(api)
    buy(api, h)
    d = api.post("/v1/me/subscription/fake/expire", headers=h).json()
    assert d["premium"] is False and d["expires_at"] is None


def test_premium_is_decided_by_dates_and_refunds(api):
    with api.session_factory() as db:
        u = User(google_sub="s1", email="s1@example.com")
        db.add(u)
        db.flush()
        now = datetime(2027, 1, 10, tzinfo=timezone.utc)
        db.add(Subscription(user_id=u.id, product_id="monthly", source="fake", purchase_token="fake:monthly:paid:one11111",
                            expires_at=now + timedelta(days=3)))
        db.commit()
        db.refresh(u)
        assert service.is_premium(u, now) and not service.is_premium(u, now + timedelta(days=3, seconds=1))
        u.subscriptions[0].revoked_at = now  # a refund ends it at once
        assert not service.is_premium(u, now)
        assert not service.is_premium(None)


def test_the_fake_store_only_believes_its_own_tokens():
    v = FakeVerifier()
    now = datetime(2027, 1, 1, tzinfo=timezone.utc)
    assert v.verify("monthly", "fake:monthly:trial:xx", now).trial
    with pytest.raises(InvalidPurchase):
        v.verify("monthly", "fake:monthly", now)


def test_export_lists_subscriptions_without_the_token(api, fake_store):
    h = login(api)
    buy(api, h)
    exp = api.get("/v1/me/export", headers=h)
    assert TOKEN not in exp.text
    s = exp.json()["subscriptions"]
    assert len(s) == 1 and s[0]["product_id"] == "monthly" and s[0]["source"] == "fake"


def test_deleting_the_account_removes_subscriptions(api, fake_store):
    h = login(api)
    buy(api, h)
    assert api.delete("/v1/me", headers=h).status_code == 204
    with api.session_factory() as db:
        assert db.query(Subscription).count() == 0


# ---------------------------------------------------------------- what free accounts get

def test_chat_limit_is_5_for_free_and_30_for_premium(api, fake_store, paywall):
    h = login(api)
    with api.session_factory() as db:
        user = db.query(User).one()
        assert service.chat_limit(user) == 5
    buy(api, h)
    with api.session_factory() as db:
        assert service.chat_limit(db.query(User).one()) == 30


def test_free_account_sees_today_and_tomorrow_but_not_the_days_after(api, paywall):
    h = login(api)
    profile(api, h)
    for d in (today(), today() + timedelta(days=1)):
        assert api.get("/v1/me/horoscope", headers=h, params={"date": d.isoformat()}).status_code == 200
    late = api.get("/v1/me/horoscope", headers=h, params={"date": (today() + timedelta(days=2)).isoformat()})
    assert late.status_code == 402 and late.json()["detail"] == "premium_required"
    past = api.get("/v1/me/horoscope", headers=h, params={"date": (today() - timedelta(days=30)).isoformat()})
    assert past.status_code == 200  # looking back is free


def test_free_card_has_score_and_suggestions_but_not_the_times(api, paywall):
    h = login(api)
    profile(api, h)
    c = api.get("/v1/me/horoscope", headers=h).json()
    assert c["score"] and c["dos"] and c["windows_locked"] is True
    assert c["windows"] == {"best": [], "avoid": []}


def test_premium_card_has_the_times_and_any_day(api, fake_store, paywall):
    h = login(api)
    profile(api, h)
    buy(api, h)
    c = api.get("/v1/me/horoscope", headers=h).json()
    assert c["windows_locked"] is False and c["windows"]["best"] and c["windows"]["avoid"]
    assert api.get("/v1/me/horoscope", headers=h,
                   params={"date": (today() + timedelta(days=40)).isoformat()}).status_code == 200


def test_the_profile_card_route_has_the_same_limits(api, paywall):
    h = login(api)
    pid = profile(api, h)["id"]
    ok = api.get(f"/v1/profiles/{pid}/horoscope", headers=h)
    assert ok.status_code == 200 and ok.json()["windows_locked"] is True
    far = api.get(f"/v1/profiles/{pid}/horoscope", headers=h, params={"date": (today() + timedelta(days=5)).isoformat()})
    assert far.status_code == 402


def test_written_horoscope_and_planet_cards_are_premium(api, paywall):
    h = login(api)
    profile(api, h)
    assert api.get("/v1/me/horoscope/text", headers=h).status_code == 402
    assert api.get("/v1/me/horoscope/planets", headers=h).status_code == 402


def test_a_written_horoscope_saved_during_a_subscription_stays_hidden_after_it_ends(api, fake_store, paywall):
    from astrodaily.api.daily_text_routes import get_daily_llm_client
    from astrodaily.main import app
    from test_daily_text import FakeLlm
    app.dependency_overrides[get_daily_llm_client] = lambda: FakeLlm()
    try:
        h = login(api)
        profile(api, h)
        buy(api, h)
        assert api.get("/v1/me/horoscope/text", headers=h).status_code == 200
        api.post("/v1/me/subscription/fake/expire", headers=h)
        assert api.get("/v1/me/horoscope/text", headers=h).status_code == 402
    finally:
        app.dependency_overrides.pop(get_daily_llm_client, None)


def test_month_for_a_free_account_locks_the_days_after_tomorrow(api, paywall):
    h = login(api)
    profile(api, h)
    t = today()
    r = api.get("/v1/me/horoscope/month", headers=h, params={"month": f"{t.year}-{t.month:02d}"}).json()
    by_day = {date.fromisoformat(d["date"]): d for d in r["days"]}
    for day, d in by_day.items():
        if day > t + timedelta(days=1):
            assert d["locked"] is True and d["score"] == 0 and d["tithi"] >= 1 and d["tithi_name"]["en"]
            assert d["special"] is None
        else:
            assert d["locked"] is False and 1 <= d["score"] <= 5


def test_month_for_a_premium_account_has_no_locks(api, fake_store, paywall):
    h = login(api)
    profile(api, h)
    buy(api, h)
    t = today()
    r = api.get("/v1/me/horoscope/month", headers=h, params={"month": f"{t.year}-{t.month:02d}"}).json()
    assert not any(d["locked"] for d in r["days"]) and all(1 <= d["score"] <= 5 for d in r["days"])


def test_far_future_month_is_locked_for_free_but_the_festivals_still_show(api, paywall):
    h = login(api)
    profile(api, h)
    r = api.get("/v1/me/horoscope/month", headers=h, params={"month": "2027-11"}).json()
    assert all(d["locked"] for d in r["days"])
    diwali = [d for d in r["days"] if d["festivals"]]
    assert diwali and all(f["en"] and f["hi"] for d in diwali for f in d["festivals"])


def test_widget_and_daily_push_leave_out_the_times_for_free_accounts(api, fake_store, paywall):
    from astrodaily.notify.message import daily_push
    h = login(api)
    profile(api, h)
    w = api.get("/v1/me/horoscope/widget", headers=h).json()
    assert w["best_window"] is None and w["avoid_window"] is None and w["headline"]
    buy(api, h)
    assert api.get("/v1/me/horoscope/widget", headers=h).json()["best_window"] is not None
    card = {"date": date(2026, 11, 28), "score": 4, "location": {"timezone": "Asia/Kolkata"},
            "dos": [{"text": "A steady day.", "reason": ""}],
            "windows": {"best": [{"start": datetime(2026, 11, 28, 4, 45, tzinfo=timezone.utc),
                                  "end": datetime(2026, 11, 28, 5, 30, tzinfo=timezone.utc)}]}}
    assert "Best time" in daily_push(card, "en").body
    assert daily_push(card, "en", with_window=False).body == "A steady day."


def test_free_chat_stops_at_the_free_limit_and_premium_goes_on(api, fake_store, paywall, monkeypatch):
    from test_chat import FakeLlm, convo, say, use_llm
    h = login(api)
    profile(api, h)
    use_llm(FakeLlm())
    cid = convo(api, h)
    left = [say(api, h, cid).json()["remaining_today"] for _ in range(5)]
    assert left == [4, 3, 2, 1, 0]
    assert say(api, h, cid).status_code == 429
    buy(api, h)
    assert say(api, h, cid).json()["remaining_today"] == 24  # 30 for premium, 6 used
