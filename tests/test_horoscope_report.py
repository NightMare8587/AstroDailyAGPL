"""Tests for selection, golden days, determinism/threading, and Level A/B report building."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timezone

from astrodaily.calc.kundli import compute_chart, resolve_birth_moment
from astrodaily.horoscope import (
    AREAS,
    ENGINE_VERSION,
    RULESET_VERSION,
    NatalContext,
    Signal,
    build_day_report,
    natal_from_chart,
    select,
)


def _sig(sig_id: str, kind: str, total: float, scope: str = "daily") -> Signal:
    per = total / len(AREAS)
    return Signal(sig_id, {}, {a: per for a in AREAS}, f"reason {sig_id}", kind, scope)  # type: ignore[arg-type]


def test_selection_prefers_daily_over_standing_and_falls_back_to_fill_slots():
    signals = [
        _sig("f_standing_huge", "favourable", 5.0, scope="standing"),
        _sig("f_standing_big", "favourable", 4.0, scope="standing"),
        _sig("f_daily_small", "favourable", 0.5, scope="daily"),
        _sig("f_daily_med", "favourable", 1.0, scope="daily"),
        _sig("u_standing_huge", "unfavourable", -5.0, scope="standing"),
        _sig("u_standing_big", "unfavourable", -4.0, scope="standing"),
        _sig("u_daily_1", "unfavourable", -0.3, scope="daily"),
    ]
    sel = select(signals)
    # 2 daily + 1 strongest standing to fill 3rd slot
    assert [s.id for s in sel.favourable] == ["f_daily_med", "f_daily_small", "f_standing_huge"]
    # 1 daily + 2 strongest standing to fill remaining 2 slots
    assert [s.id for s in sel.unfavourable] == ["u_daily_1", "u_standing_huge", "u_standing_big"]


def test_signal_scopes_on_real_report():
    bm = resolve_birth_moment(date(1990, 5, 15), time(10, 0), "Asia/Kolkata", None)
    ch = compute_chart(bm, 28.6139, 77.2090, as_of=datetime(2025, 3, 20, 6, 30, tzinfo=timezone.utc))
    natal = natal_from_chart(ch, as_of=datetime(2025, 3, 20, 6, 30, tzinfo=timezone.utc))
    rep = build_day_report(date(2025, 3, 20), 19.0760, 72.8777, "Asia/Kolkata", natal)
    by_id = {s.id: s for s in rep.signals}
    for slow_id in ("gochara_jupiter_poor", "gochara_saturn_good", "gochara_rahu_poor", "gochara_ketu_poor", "dasha_rahu_venus"):
        assert by_id[slow_id].scope == "standing"
    for daily_id in ("chandra_bala_poor", "tara_sadhana", "gochara_sun_poor", "vara_thursday", "mercury_retrograde", "coming_up_saturn_ingress"):
        assert by_id[daily_id].scope == "daily"


def test_selection_caps_tie_break_and_freshness():
    signals = [
        _sig("f_strong", "favourable", 2.0),
        _sig("f_tie_seen", "favourable", 1.0),
        _sig("f_tie_b", "favourable", 1.0),
        _sig("f_tie_a", "favourable", 1.0),
        _sig("u_1", "unfavourable", -1.5),
        _sig("u_2", "unfavourable", -1.2),
        _sig("u_3", "unfavourable", -0.8),
        _sig("u_4", "unfavourable", -0.4),
        _sig("t_strong", "theme", -0.9),
        _sig("t_weak", "theme", 0.3),
        _sig("c_a", "coming_up", 0.0),
        _sig("c_b", "coming_up", 0.0),
    ]
    sel = select(signals, recently_shown={"f_tie_seen", "c_a"})
    assert [s.id for s in sel.favourable] == ["f_strong", "f_tie_a", "f_tie_b"]
    assert [s.id for s in sel.unfavourable] == ["u_1", "u_2", "u_3"]
    assert sel.theme is not None and sel.theme.id == "t_strong"
    assert sel.coming_up is not None and sel.coming_up.id == "c_b"


def test_golden_days():
    """Three fixed (profile, date) pairs with expected signal IDs derived independently."""
    # Golden Day 1: 2025-10-21 (Diwali Amavasya), Delhi, Level A (Moon in Leo = 5).
    # Verified with ndastro_engine (Lahiri, mean node) at sunrise 2025-10-21T00:56Z:
    # Sun=7(h3), Moon=6(h2), Mars=7(h3), Mercury=7(h3,dir), Jupiter=4(h12), Venus=6(h2),
    # Saturn=12(h8 -> ashtama), Rahu=11(h7), Ketu=5(h1); Amavasya, Naga, Vishkambha, Tuesday.
    rep1 = build_day_report(date(2025, 10, 21), 28.6139, 77.2090, "Asia/Kolkata", NatalContext(moon_sign=5))
    assert rep1.level == "A"
    assert {s.id for s in rep1.signals} == {
        "chandra_bala_poor",
        "gochara_sun_good",
        "gochara_mars_good",
        "gochara_mercury_poor",
        "gochara_jupiter_poor",
        "gochara_venus_good",
        "gochara_saturn_poor",
        "gochara_rahu_poor",
        "gochara_ketu_poor",
        "ashtama_shani",
        "amavasya",
        "vara_tuesday",
    }

    # Golden Day 2: 2025-03-20, Mumbai, Level B (birth 1990-05-15 10:00 IST Delhi).
    # Natal: Moon=9 (Sagittarius), nak=21 (Uttara Ashadha), Lagna=4, Dasha=Rahu-Venus.
    # Transits at sunrise 2025-03-20T01:13Z: Sun=12(h4), Moon=8(h12), Mars=3(h7),
    # Mercury=12(h4,retro), Jupiter=2(h6), Venus=12(h4), Saturn=11(h3, enters 12 on Mar 29),
    # Rahu=12(h4), Ketu=6(h10); nak=17 (count 24 -> tara 6 Sadhana); Shashthi, Vajra, Gara, Thu.
    bm1 = resolve_birth_moment(date(1990, 5, 15), time(10, 0), "Asia/Kolkata", None)
    ch1 = compute_chart(bm1, 28.6139, 77.2090, as_of=datetime(2025, 3, 20, 6, 30, tzinfo=timezone.utc))
    natal1 = natal_from_chart(ch1, as_of=datetime(2025, 3, 20, 6, 30, tzinfo=timezone.utc))
    rep2 = build_day_report(date(2025, 3, 20), 19.0760, 72.8777, "Asia/Kolkata", natal1)
    assert rep2.level == "B"
    assert {s.id for s in rep2.signals} == {
        "chandra_bala_poor",
        "tara_sadhana",
        "gochara_sun_poor",
        "gochara_mars_poor",
        "gochara_mercury_good",
        "gochara_jupiter_poor",
        "gochara_venus_good",
        "gochara_saturn_good",
        "gochara_rahu_poor",
        "gochara_ketu_poor",
        "dasha_rahu_venus",
        "vara_thursday",
        "mercury_retrograde",
        "coming_up_saturn_ingress",
    }

    # Golden Day 3: 2025-11-05 (Kartik Purnima), Chennai, Level B (birth 1972-11-22 05:10 IST Chennai).
    # Natal: Moon=2 (Taurus), nak=4 (Rohini), Lagna=7, Dasha=Saturn-Sun.
    # Transits at sunrise 2025-11-05T00:34Z: Sun=7(h6), Moon=1(h12), Mars=8(h7),
    # Mercury=8(h7,dir), Jupiter=4(h3), Venus=7(h6), Saturn=12(h11), Rahu=11(h10), Ketu=5(h4);
    # nak=1 (count 25 -> tara 7 Naidhana); Purnima, Siddhi, Vishti (Bhadra), Wed.
    bm2 = resolve_birth_moment(date(1972, 11, 22), time(5, 10), "Asia/Kolkata", None)
    ch2 = compute_chart(bm2, 13.0827, 80.2707, as_of=datetime(2025, 11, 5, 6, 30, tzinfo=timezone.utc))
    natal2 = natal_from_chart(ch2, as_of=datetime(2025, 11, 5, 6, 30, tzinfo=timezone.utc))
    rep3 = build_day_report(date(2025, 11, 5), 13.0827, 80.2707, "Asia/Kolkata", natal2)
    assert rep3.level == "B"
    assert {s.id for s in rep3.signals} == {
        "chandra_bala_poor",
        "tara_naidhana",
        "gochara_sun_good",
        "gochara_mars_poor",
        "gochara_mercury_poor",
        "gochara_jupiter_poor",
        "gochara_venus_poor",
        "gochara_saturn_good",
        "gochara_rahu_good",
        "gochara_ketu_poor",
        "dasha_saturn_sun",
        "vishti_karana",
        "vara_wednesday",
    }


def test_determinism_and_thread_pool_consistency():
    natal = NatalContext(moon_sign=5)
    baseline = build_day_report(date(2025, 5, 10), 28.6139, 77.2090, "Asia/Kolkata", natal)
    second = build_day_report(date(2025, 5, 10), 28.6139, 77.2090, "Asia/Kolkata", natal)
    assert baseline == second
    assert baseline.engine_version == ENGINE_VERSION
    assert baseline.ruleset_version == RULESET_VERSION

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(
            lambda _: build_day_report(date(2025, 5, 10), 28.6139, 77.2090, "Asia/Kolkata", natal),
            range(12),
        ))
    assert all(r == baseline for r in results)


def test_level_a_without_birth_time_and_level_b_from_chart():
    # Level A: only moon_sign
    rep_a = build_day_report(date(2025, 6, 15), 28.6139, 77.2090, "Asia/Kolkata", NatalContext(moon_sign=1))
    assert rep_a.level == "A"
    assert not any(s.id.startswith("tara_") or s.id.startswith("dasha_") for s in rep_a.signals)
    assert 1 <= rep_a.score <= 5 and set(rep_a.areas.keys()) == set(AREAS)

    # Level None: panchang-only day report
    rep_none = build_day_report(date(2025, 6, 15), 28.6139, 77.2090, "Asia/Kolkata", None)
    assert rep_none.level == "A"
    assert any(s.kind == "info" for s in rep_none.signals)

    # Level B from compute_chart
    bm = resolve_birth_moment(date(1990, 5, 15), time(10, 0), "Asia/Kolkata", None)
    chart = compute_chart(bm, 28.6139, 77.2090, as_of=datetime(2025, 6, 15, 6, 30, tzinfo=timezone.utc))
    natal_b = natal_from_chart(chart)
    rep_b = build_day_report(date(2025, 6, 15), 28.6139, 77.2090, "Asia/Kolkata", natal_b)
    assert rep_b.level == "B"
    assert any(s.id.startswith("tara_") for s in rep_b.signals)
    assert any(s.id.startswith("dasha_") for s in rep_b.signals)
