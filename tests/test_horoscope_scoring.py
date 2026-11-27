"""Tests for astrodaily.horoscope.weights and scoring."""
import random
from datetime import date, timedelta
from statistics import mean

import pytest

from astrodaily.horoscope import NatalContext, build_day_report, rules, weights
from astrodaily.horoscope.scoring import area_scores, day_score
from astrodaily.horoscope.signals import Signal


def test_weight_table_bounds_and_slow_planet_dominance():
    for sig_id, row in weights.WEIGHTS.items():
        assert set(row.keys()) == set(weights.AREAS), sig_id
        for area, val in row.items():
            assert -2.0 <= val <= 2.0, f"{sig_id}.{area}={val}"

    fast = ("sun", "mars", "mercury", "venus")
    slow = ("jupiter", "saturn", "rahu", "ketu")
    for polarity in ("good", "poor"):
        max_fast = max(sum(abs(v) for v in weights.WEIGHTS[f"gochara_{p}_{polarity}"].values()) for p in fast)
        min_slow = min(sum(abs(v) for v in weights.WEIGHTS[f"gochara_{p}_{polarity}"].values()) for p in slow)
        assert min_slow > max_fast, f"Expected slow > fast for {polarity}"


def test_neutral_input_gives_3_everywhere():
    assert area_scores([]) == {a: 3 for a in weights.AREAS}
    assert day_score({a: 3 for a in weights.AREAS}, []) == 3

    zero_sig = Signal("info_x", {}, {a: 0.0 for a in weights.AREAS}, "neutral", "info")
    areas = area_scores([zero_sig])
    assert areas == {a: 3 for a in weights.AREAS}
    assert day_score(areas, [zero_sig]) == 3


def test_scoring_bounded_1_to_5_randomised_and_extreme():
    rng = random.Random(42)
    for _ in range(200):
        n = rng.randint(0, 30)
        sigs = []
        for i in range(n):
            kind = rng.choice(["favourable", "unfavourable", "theme", "info"])
            w = {a: rng.uniform(-2.0, 2.0) for a in weights.AREAS}
            sigs.append(Signal(f"s_{i}", {}, w, "test", kind))  # type: ignore[arg-type]
        areas = area_scores(sigs)
        assert set(areas.keys()) == set(weights.AREAS)
        assert all(1 <= v <= 5 for v in areas.values())
        score = day_score(areas, sigs)
        assert 1 <= score <= 5

    # Extreme positive
    pos = [Signal(f"p_{i}", {}, {a: 2.0 for a in weights.AREAS}, "pos", "favourable") for i in range(20)]
    pos_areas = area_scores(pos)
    assert all(v == 5 for v in pos_areas.values())
    assert day_score(pos_areas, pos) == 5

    # Extreme negative produces 1
    neg = [Signal(f"n_{i}", {}, {a: -2.0 for a in weights.AREAS}, "neg", "unfavourable") for i in range(10)]
    neg_areas = area_scores(neg)
    assert all(v == 1 for v in neg_areas.values())
    assert day_score(neg_areas, neg) == 1


def test_rule_tables_are_centred_at_zero_expectation():
    for area in weights.AREAS:
        # Chandra Bala (6/12 good, 6/12 poor)
        cb_exp = sum(
            weights.WEIGHTS["chandra_bala_good" if h in rules.CHANDRA_BALA_GOOD_HOUSES else "chandra_bala_poor"][area]
            for h in range(1, 13)
        ) / 12.0
        assert cb_exp == pytest.approx(0.0, abs=1e-9)

        # Gochara for each non-Moon planet under uniform 1..12 houses
        for planet, good_houses in rules.GOCHARA_FAVOURABLE_HOUSES.items():
            if planet == "Moon":
                continue
            p_exp = sum(
                weights.WEIGHTS[f"gochara_{planet.lower()}_{'good' if h in good_houses else 'poor'}"][area]
                for h in range(1, 13)
            ) / 12.0
            assert p_exp == pytest.approx(0.0, abs=1e-9), (planet, area)

        # Tara Bala under uniform 1..27 nakshatra counts
        tara_exp = sum(
            weights.WEIGHTS[f"tara_{rules.TARA_TABLE[(c - 1) % 9 + 1][0]}"][area]
            for c in range(1, 28)
        ) / 27.0
        assert tara_exp == pytest.approx(0.0, abs=1e-9), area

        # Nakshatra categories across 1..27
        nak_exp = sum(
            weights.WEIGHTS[f"nakshatra_{rules.NAKSHATRA_CATEGORY_BY_NUM[n]}"][area]
            for n in range(1, 28)
        ) / 27.0
        assert nak_exp == pytest.approx(0.0, abs=1e-9), area

        # Tithi categories across 1..30 (tithi 30 is Amavasya)
        tithi_exp = sum(
            weights.WEIGHTS[
                "amavasya" if t == rules.AMAVASYA_TITHI_NUMBER else rules.TITHI_SIGNAL_BY_PAKSHA_NUM[(t - 1) % 15 + 1]
            ][area]
            for t in range(1, 31)
        ) / 30.0
        assert tithi_exp == pytest.approx(0.0, abs=1e-9), area

        # Dasha base is 0 and house tone is centred across 1..12
        assert weights.WEIGHTS["dasha_base"][area] == pytest.approx(0.0, abs=1e-9)
        assert sum(rules.DASHA_HOUSE_TONE.values()) == pytest.approx(0.0, abs=1e-9)

        # Saturn cycles: 5/12 houses emit negative theme; subtracted by expected_saturn_cycle_drift
        sat_exp = sum(weights.WEIGHTS[k][area] for k in weights.SATURN_CYCLE_KEYS) / 12.0
        assert sat_exp - weights.expected_saturn_cycle_drift()[area] == pytest.approx(0.0, abs=1e-9), area

        # Remaining one-sided Panchang penalties (Vishti 8/60, inauspicious yogas 7/27)
        assert set(weights.PANCHANG_FREQUENCIES.keys()) == {"vishti_karana", "inauspicious_yoga"}
        pan_exp = (
            (8.0 / 60.0) * weights.WEIGHTS["vishti_karana"][area]
            + (len(rules.INAUSPICIOUS_YOGAS) / 27.0) * weights.WEIGHTS["inauspicious_yoga"][area]
        )
        assert pan_exp - weights.expected_panchang_drift()[area] == pytest.approx(0.0, abs=1e-9), area


def test_level_a_score_distribution_balanced():
    days = [date(2025, 1, 1) + timedelta(days=i) for i in range(0, 365, 9)]
    scores = [
        build_day_report(d, 28.6139, 77.2090, "Asia/Kolkata", NatalContext(moon_sign=sign)).score
        for sign in range(1, 13)
        for d in days
    ]
    assert 2.7 <= mean(scores) <= 3.3
    assert any(s <= 2 for s in scores)
    assert any(s >= 4 for s in scores)


def test_single_signal_from_weight_table_cannot_swing_area_to_extremes():
    for sig_id, row in weights.WEIGHTS.items():
        sig = Signal(sig_id, {}, dict(row), "single", "favourable")
        areas = area_scores([sig])
        assert all(2 <= v <= 4 for v in areas.values()), f"{sig_id} swung an area to 1 or 5 alone"


def test_monkeypatch_weight_table_changes_scores(monkeypatch):
    from datetime import date
    from astrodaily.horoscope.report import build_day_report
    from astrodaily.horoscope.signals import NatalContext

    natal = NatalContext(moon_sign=5)
    base = build_day_report(date(2025, 10, 21), 28.6139, 77.2090, "Asia/Kolkata", natal)

    boosted = {k: dict(v) for k, v in weights.WEIGHTS.items()}
    for sig_id in boosted:
        boosted[sig_id] = {a: 2.0 for a in weights.AREAS}
    monkeypatch.setattr(weights, "WEIGHTS", boosted)

    after = build_day_report(date(2025, 10, 21), 28.6139, 77.2090, "Asia/Kolkata", natal)
    assert after.score > base.score
    assert all(after.areas[a] >= base.areas[a] for a in weights.AREAS)
