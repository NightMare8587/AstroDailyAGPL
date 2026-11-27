"""Tests for astrodaily.horoscope.windows (best_windows and avoid_windows)."""
from datetime import date, timedelta

from astrodaily.calc.panchang import compute_panchang
from astrodaily.horoscope.windows import _daytime_choghadiya, avoid_windows, best_windows


def _overlaps(a_start, a_end, b_start, b_end) -> bool:
    return max(a_start, b_start) < min(a_end, b_end)


SAMPLE_CASES = [
    # Delhi across weekdays and seasons
    (date(2025, 1, 5), 28.6139, 77.2090, "Asia/Kolkata"),
    (date(2025, 3, 20), 28.6139, 77.2090, "Asia/Kolkata"),
    (date(2025, 6, 21), 28.6139, 77.2090, "Asia/Kolkata"),
    (date(2025, 10, 21), 28.6139, 77.2090, "Asia/Kolkata"),
    (date(2025, 11, 5), 28.6139, 77.2090, "Asia/Kolkata"),
    # Mumbai, Chennai, New York
    (date(2025, 4, 14), 19.0760, 72.8777, "Asia/Kolkata"),
    (date(2025, 8, 15), 13.0827, 80.2707, "Asia/Kolkata"),
    (date(2025, 9, 22), 40.7128, -74.0060, "America/New_York"),
    # High-latitude place (Tromso, Norway in spring and autumn)
    (date(2025, 4, 10), 69.6492, 18.9553, "Europe/Oslo"),
    (date(2025, 10, 15), 69.6492, 18.9553, "Europe/Oslo"),
    # Unusually short winter day (Stockholm winter solstice, ~6h daylight: 45-min choghadiya boundary)
    (date(2025, 12, 21), 59.3293, 18.0686, "Europe/Stockholm"),
    # Very short winter day (Reykjavik winter solstice, ~4h daylight: < 45-min slots)
    (date(2025, 12, 21), 64.1466, -21.9426, "Atlantic/Reykjavik"),
]


def test_windows_invariants_across_dates_and_latitudes():
    for day, lat, lon, tz in SAMPLE_CASES:
        p = compute_panchang(day, lat, lon, tz)
        blocked = [p["rahu_kaal"], p["gulika_kaal"], p["yamaganda"]]

        for limit in (1, 2, 3):
            best = best_windows(p, limit=limit)
            assert len(best) <= limit
            assert best == best_windows(p, limit=limit)  # deterministic
            for w in best:
                assert (w.end - w.start) >= timedelta(minutes=45)
                assert w.start >= p["sunrise"] and w.end <= p["sunset"]
                for blk in blocked:
                    assert not _overlaps(w.start, w.end, blk.start, blk.end), (day, w, blk)

        avoid = avoid_windows(p)
        assert avoid == avoid_windows(p)
        assert any(
            w.label == "Rahu Kaal" and w.start == p["rahu_kaal"].start and w.end == p["rahu_kaal"].end
            for w in avoid
        )
        for w in avoid:
            assert w.start >= p["sunrise"] and w.end <= p["sunset"]


def test_unusually_short_day_returns_no_sub_45min_windows():
    # Reykjavik on Dec 21 has ~4h08m of daylight -> each 1/8th slot is ~31 min (< 45 min).
    p = compute_panchang(date(2025, 12, 21), 64.1466, -21.9426, "Atlantic/Reykjavik")
    assert best_windows(p, limit=2) == []
    assert any(w.label == "Rahu Kaal" for w in avoid_windows(p))


def test_all_eight_daytime_slots_considered_over_many_days_and_places():
    places = [
        (28.6139, 77.2090, "Asia/Kolkata"),       # Delhi
        (13.0827, 80.2707, "Asia/Kolkata"),       # Chennai
        (64.1466, -21.9426, "Atlantic/Reykjavik"), # Reykjavik (high latitude, rises/sets year-round)
    ]
    checked = 0
    for lat, lon, tz in places:
        for offset in range(0, 360, 9):  # 40 days across the whole year per place = 120 days
            day = date(2025, 1, 1) + timedelta(days=offset)
            p = compute_panchang(day, lat, lon, tz)
            assert len(_daytime_choghadiya(p)) == 8, (day, tz)
            checked += 1
    assert checked >= 100


def test_last_daytime_slot_included_in_best_and_avoid():
    # On Monday (2025-01-06, Delhi), slot 7 (8th daytime slot) is Amrit and does not overlap
    # Rahu Kaal (seg 2), Gulika (seg 6), or Yamaganda (seg 3).
    p_mon = compute_panchang(date(2025, 1, 6), 28.6139, 77.2090, "Asia/Kolkata")
    last_mon = _daytime_choghadiya(p_mon)[7]
    assert last_mon.en == "Amrit"
    best_mon = best_windows(p_mon, limit=2)
    assert any(w.label == "Amrit" and w.start == last_mon.start for w in best_mon)

    # On Tuesday (2025-01-07, Delhi), slot 7 (8th daytime slot) is Rog and must appear in avoid_windows.
    p_tue = compute_panchang(date(2025, 1, 7), 28.6139, 77.2090, "Asia/Kolkata")
    last_tue = _daytime_choghadiya(p_tue)[7]
    assert last_tue.en == "Rog"
    avoid_tue = avoid_windows(p_tue)
    assert any(w.label == "Rog" and w.start == last_tue.start for w in avoid_tue)


def test_abhijit_window_not_offered_on_wednesday():
    from datetime import date
    from astrodaily.calc.panchang import compute_panchang
    wed = compute_panchang(date(2025, 3, 19), 28.6139, 77.2090, "Asia/Kolkata")
    assert wed["sunrise"].weekday() == 2
    assert all(w.label != "Abhijit Muhurat" for w in best_windows(wed, limit=20))
    thu = compute_panchang(date(2025, 3, 20), 28.6139, 77.2090, "Asia/Kolkata")
    assert any(w.label == "Abhijit Muhurat" for w in best_windows(thu, limit=20))
