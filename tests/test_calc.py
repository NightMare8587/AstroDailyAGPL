import pytest
from datetime import date, datetime, timedelta, timezone

from astrodaily.calc import ephem, names
from astrodaily.calc.panchang import (
    GULIKA_SEGMENT, RAHU_SEGMENT, YAMAGANDA_SEGMENT, choghadiya_slots,
    compute_panchang, karana_name, split_segments, tithi_name,
)

DELHI = (28.6139, 77.2090, "Asia/Kolkata")


def test_lahiri_ayanamsa_j2000():
    jd = ephem.datetime_to_jd(datetime(2000, 1, 1, 12, tzinfo=timezone.utc))
    assert abs(ephem.ayanamsa(jd) - 23.857) < 0.01


def test_makar_sankranti_2025_sun_enters_sidereal_capricorn():
    before = ephem.datetime_to_jd(datetime(2025, 1, 14, 3, 0, tzinfo=timezone.utc))  # 08:30 IST
    after = ephem.datetime_to_jd(datetime(2025, 1, 14, 4, 30, tzinfo=timezone.utc))  # 10:00 IST
    assert ephem.sidereal_longitude(before, ephem.SUN) < 270.0
    assert ephem.sidereal_longitude(after, ephem.SUN) >= 270.0


def test_known_tithis_diwali_and_kartik_purnima_2025_delhi():
    d20 = compute_panchang(date(2025, 10, 20), *DELHI)
    d21 = compute_panchang(date(2025, 10, 21), *DELHI)
    d5 = compute_panchang(date(2025, 11, 5), *DELHI)
    assert d20["tithi"].en == "Chaturdashi" and d20["tithi"].extra["paksha"] == "krishna"
    assert d21["tithi"].en == "Amavasya" and d21["tithi"].number == 30
    assert d5["tithi"].en == "Purnima" and d5["tithi"].number == 15
    # Published end times, minutes of tolerance.
    assert abs((d21["tithi"].ends_at - d21["tithi"].ends_at.replace(hour=17, minute=54, second=0)).total_seconds()) < 180
    assert abs((d5["tithi"].ends_at - d5["tithi"].ends_at.replace(hour=18, minute=48, second=0)).total_seconds()) < 180


def test_sunrise_sunset_delhi_sane():
    p = compute_panchang(date(2025, 10, 20), *DELHI)
    assert p["sunrise"].strftime("%H:%M") in ("06:24", "06:25", "06:26")
    assert timedelta(hours=10) < p["sunset"] - p["sunrise"] < timedelta(hours=12)


def test_rahu_kaal_monday_and_sunday_on_6_to_18_day():
    start = datetime(2026, 1, 5, 6, 0)
    end = datetime(2026, 1, 5, 18, 0)
    segs = split_segments(start, end, 8)
    monday = (1)  # Sunday-first index
    s, e = segs[RAHU_SEGMENT[monday] - 1]
    assert (s.hour, s.minute, e.hour, e.minute) == (7, 30, 9, 0)
    s, e = segs[RAHU_SEGMENT[0] - 1]  # Sunday
    assert (s.hour, s.minute, e.hour, e.minute) == (16, 30, 18, 0)


def test_segment_tables_are_permutations():
    assert sorted(RAHU_SEGMENT) == [2, 3, 4, 5, 6, 7, 8]  # Rahu is never in the first segment
    for table in (GULIKA_SEGMENT, YAMAGANDA_SEGMENT):
        assert sorted(table) == [1, 2, 3, 4, 5, 6, 7]


def test_choghadiya_matches_published_tables():
    sunrise = datetime(2026, 1, 4, 6, 0)
    sunset = datetime(2026, 1, 4, 18, 0)
    nxt = datetime(2026, 1, 5, 6, 0)
    sun = choghadiya_slots(0, sunrise, sunset, nxt)
    assert [s.en for s in sun[:8]] == ["Udveg", "Char", "Labh", "Amrit", "Kaal", "Shubh", "Rog", "Udveg"]
    assert [s.en for s in sun[8:]] == ["Shubh", "Amrit", "Char", "Rog", "Kaal", "Labh", "Udveg", "Shubh"]
    mon = choghadiya_slots(1, sunrise, sunset, nxt)
    assert [s.en for s in mon[:8]] == ["Amrit", "Kaal", "Shubh", "Rog", "Udveg", "Char", "Labh", "Amrit"]
    assert [s.en for s in mon[8:]] == ["Char", "Rog", "Kaal", "Labh", "Udveg", "Shubh", "Amrit", "Char"]
    sat = choghadiya_slots(6, sunrise, sunset, nxt)
    assert [s.en for s in sat[:8]] == ["Kaal", "Shubh", "Rog", "Udveg", "Char", "Labh", "Amrit", "Kaal"]
    assert [s.en for s in sat[8:]] == ["Labh", "Udveg", "Shubh", "Amrit", "Char", "Rog", "Kaal", "Labh"]
    assert sun[0].start == sunrise and sun[8].start == sunset and sun[15].end == nxt


def test_name_helpers():
    assert tithi_name(0)[:2] == ("Pratipada", "प्रतिपदा")
    assert tithi_name(14)[0] == "Purnima" and tithi_name(29)[0] == "Amavasya"
    assert tithi_name(15)[2] == "krishna"
    assert karana_name(0)[0] == "Kimstughna" and karana_name(59)[0] == "Naga"
    assert karana_name(1)[0] == "Bava" and karana_name(7)[0] == "Vishti (Bhadra)" and karana_name(8)[0] == "Bava"
    assert len(names.NAKSHATRA) == 27 and len(names.YOGA) == 27


def test_abhijit_is_eighth_of_fifteen_day_muhurtas():
    p = compute_panchang(date(2025, 10, 20), *DELHI)
    day = p["sunset"] - p["sunrise"]
    assert abs((p["abhijit"].end - p["abhijit"].start) - day / 15) < timedelta(seconds=1)
    mid = p["sunrise"] + day / 2
    assert p["abhijit"].start < mid < p["abhijit"].end


def test_elements_end_after_sunrise():
    p = compute_panchang(date(2026, 3, 14), *DELHI)
    for key in ("tithi", "nakshatra", "yoga", "karana"):
        assert p[key].ends_at > p["sunrise"]


def test_sidereal_mode_is_reapplied_on_every_call():
    """Regression: on Linux the sidereal mode set at start-up was invisible to worker threads, so the
    server used Fagan-Bradley (0.9 degrees off Lahiri). Every calculation must set it itself."""
    import swisseph as swe
    jd = ephem.datetime_to_jd(datetime(1990, 5, 15, 4, 30, tzinfo=timezone.utc))
    expected = ephem.ayanamsa(jd)
    assert abs(expected - 23.7225) < 0.001
    for mode in (swe.SIDM_FAGAN_BRADLEY, swe.SIDM_RAMAN, swe.SIDM_KRISHNAMURTI):
        swe.set_sid_mode(mode)  # simulate a thread that has the wrong or default mode
        assert ephem.ayanamsa(jd) == pytest.approx(expected)
        swe.set_sid_mode(mode)
        lon = ephem.sidereal_longitude(jd, ephem.SUN)
        swe.set_sid_mode(mode)
        assert ephem.body_position(jd, ephem.SUN)[0] == pytest.approx(lon)
        swe.set_sid_mode(mode)
        assert ephem.ascendant(jd, 28.6, 77.2) == pytest.approx(ephem.ascendant(jd, 28.6, 77.2))
        swe.set_sid_mode(mode)
        assert abs(lon - 30.369) < 0.01  # Sun on 15 May 1990, sidereal Lahiri


def test_sidereal_mode_in_worker_threads():
    from concurrent.futures import ThreadPoolExecutor
    jd = ephem.datetime_to_jd(datetime(1990, 5, 15, 4, 30, tzinfo=timezone.utc))
    with ThreadPoolExecutor(4) as pool:
        values = list(pool.map(lambda _: ephem.ayanamsa(jd), range(8)))
    assert all(abs(v - 23.7225) < 0.001 for v in values)
