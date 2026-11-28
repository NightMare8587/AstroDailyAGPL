from datetime import date, datetime, time, timedelta, timezone

import pytest
from sqlalchemy import select

from astrodaily.calc.transits import next_station
from astrodaily.models import NotificationLog, NotificationPrefs
from astrodaily.notify import transit
from astrodaily.notify.transit import Event, events_between, run_transit_once, transit_push
from test_notifications import FakeSender, IST, db, mk  # noqa: F401  (db is a fixture)

UTC = timezone.utc


def test_saturn_turns_direct_on_10_or_11_december_2026():
    st = next_station("Saturn", datetime(2026, 11, 28, tzinfo=UTC), 30)
    assert st is not None and not st.retrograde and st.when.date() in (date(2026, 12, 10), date(2026, 12, 11))


def test_mercury_turns_retrograde_in_february_2027_and_rahu_has_no_station():
    st = next_station("Mercury", datetime(2027, 1, 1, tzinfo=UTC), 60)
    assert st is not None and st.retrograde and st.when.date() == date(2027, 2, 9)
    with pytest.raises(ValueError):
        next_station("Rahu", datetime(2027, 1, 1, tzinfo=UTC), 60)


def test_events_in_a_window_are_sorted_and_each_has_a_sign():
    ev = events_between(datetime(2026, 11, 28, tzinfo=UTC), datetime(2026, 12, 15, tzinfo=UTC))
    assert [(e.planet, e.kind) for e in ev] == [("Mercury", "in"), ("Rahu", "in"), ("Saturn", "dr"), ("Jupiter", "rx")]
    assert ev == sorted(ev, key=lambda e: e.when) and all(1 <= e.sign <= 12 for e in ev)


def test_message_text_english_and_hindi_with_the_house_from_the_moon_sign():
    e = Event("in", "Mercury", datetime(2026, 12, 2, tzinfo=UTC), 8)  # Scorpio
    en = transit_push(e, 4, "en")  # Moon in Cancer: Scorpio is the 5th house
    assert en.title == "Mercury changes sign today"
    assert en.body == "Mercury enters Scorpio, your 5th house from your Moon sign."
    hi = transit_push(e, 4, "hi")
    assert hi.title == "बुध आज राशि बदलता है" and "वृश्चिक" in hi.body and "पाँचवें" in hi.body
    assert en.data == {"type": "transit", "planet": "Mercury", "event": "in"}


def test_rahu_message_also_names_ketu_and_a_station_message():
    rahu = transit_push(Event("in", "Rahu", datetime(2026, 12, 5, tzinfo=UTC), 10), 1, "en")
    assert "Ketu moves to Cancer" in rahu.body
    rx = transit_push(Event("rx", "Mercury", datetime(2027, 2, 9, tzinfo=UTC), 11), 1, "en")
    assert rx.title == "Mercury turns retrograde today" and "is in Aquarius" in rx.body
    assert transit_push(Event("dr", "Saturn", datetime(2026, 12, 11, tzinfo=UTC), 12), 1, "hi").title == "शनि आज मार्गी होता है"


def test_the_log_tag_fits_the_column():
    assert Event("rx", "Mercury", datetime(2027, 2, 9, tzinfo=UTC), 11).log_kind == "tr:Mer:rx"
    assert len(Event("dr", "Saturn", datetime(2027, 2, 9, tzinfo=UTC), 11).log_kind) <= 16


def mk_alerts(db, **kw):
    u = mk(db, enabled=False, **kw)
    u.notification_prefs.transit_enabled = True
    db.commit()
    return u


def morning(day, h=9, m=5):
    return datetime(2026, 12, day, h, m, tzinfo=IST).astimezone(UTC)


def test_sends_the_alert_on_the_morning_of_the_event_once(db):
    mk_alerts(db)
    s = FakeSender()
    r = run_transit_once(db, s, morning(5))  # Rahu changes sign on 5 December
    assert r.sent == 1 and len(s.calls) == 1
    assert "Rahu" in s.calls[0][1].title or "Rahu" in s.calls[0][1].body
    assert run_transit_once(db, s, morning(5, 9, 40)).sent == 0  # a later run sends nothing more
    assert len(s.calls) == 1
    kinds = db.scalars(select(NotificationLog.kind)).all()
    assert kinds == ["tr:Rah:in"]


def test_nothing_before_nine_or_long_after_or_when_off(db):
    u = mk_alerts(db)
    s = FakeSender()
    assert run_transit_once(db, s, morning(5, 8, 30)).sent == 0
    assert run_transit_once(db, s, morning(5, 13, 30)).sent == 0
    u.notification_prefs.transit_enabled = False
    db.commit()
    assert run_transit_once(db, s, morning(5)).sent == 0
    assert s.calls == []


def test_daily_switch_alone_does_not_send_alerts(db):
    mk(db, enabled=True)
    s = FakeSender()
    assert run_transit_once(db, s, morning(5)).sent == 0


def test_dry_run_counts_but_writes_and_sends_nothing(db):
    mk_alerts(db)
    s = FakeSender()
    r = run_transit_once(db, s, morning(5), dry_run=True)
    assert r.sent == 1 and s.calls == [] and db.scalars(select(NotificationLog.id)).all() == []


def test_a_failed_send_is_retried_then_stops(db):
    mk_alerts(db)
    s = FakeSender("retry")
    assert run_transit_once(db, s, morning(5)).failed == 1
    assert run_transit_once(db, s, morning(5, 9, 10)).failed == 1
    assert run_transit_once(db, s, morning(5, 9, 20)).failed == 1
    assert run_transit_once(db, s, morning(5, 9, 30)).failed == 0  # three attempts in all
    assert len(s.calls) == 3
