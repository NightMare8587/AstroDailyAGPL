"""Unit tests for astrodaily.horoscope.rules and signals."""
from datetime import date, datetime, timedelta, timezone

import pytest

from astrodaily.calc.panchang import Element, Span, compute_panchang
from astrodaily.calc.transits import GrahaTransit, house_from
from astrodaily.horoscope import build_day_report, rules
from astrodaily.horoscope.signals import DayContext, NatalContext, evaluate_signals


BANNED_WORDS = ("death", "disease", "accident", "curse", "doom", "ruin")


def _make_panchang(
    *,
    tithi_num: int = 2,
    tithi_en: str = "Dwitiya",
    paksha: str = "shukla",
    nak_num: int = 1,
    nak_en: str = "Ashwini",
    yoga_num: int = 2,
    yoga_en: str = "Priti",
    karana_en: str = "Bava",
    vara_en: str = "Monday",
    sunrise: datetime | None = None,
) -> dict:
    sr = sunrise or datetime(2025, 6, 10, 0, 0, tzinfo=timezone.utc)
    end = datetime(2025, 6, 10, 12, 0, tzinfo=timezone.utc)
    return {
        "date": sr.date(),
        "timezone": "UTC",
        "sunrise": sr,
        "sunset": end,
        "next_sunrise": datetime(2025, 6, 11, 0, 0, tzinfo=timezone.utc),
        "vara": (vara_en, vara_en),
        "tithi": Element(tithi_num, tithi_en, tithi_en, end, {"paksha": paksha}),
        "nakshatra": Element(nak_num, nak_en, nak_en, end, {"pada": 1}),
        "yoga": Element(yoga_num, yoga_en, yoga_en, end, {}),
        "karana": Element(1, karana_en, karana_en, end, {}),
        "rahu_kaal": Span("Rahu Kaal", "राहु काल", sr, end),
        "gulika_kaal": Span("Gulika Kaal", "गुलिक काल", sr, end),
        "yamaganda": Span("Yamaganda", "यमगण्ड", sr, end),
        "abhijit": Span("Abhijit Muhurat", "अभिजीत मुहूर्त", sr, end),
        "choghadiya": [],
    }


def _make_transits(signs: dict[str, int] | None = None, mercury_retro: bool = False) -> dict[str, GrahaTransit]:
    base = {
        "Sun": 1, "Moon": 1, "Mars": 1, "Mercury": 1, "Jupiter": 1,
        "Venus": 1, "Saturn": 1, "Rahu": 1, "Ketu": 7,
    }
    if signs:
        base.update(signs)
    out = {}
    for k, s in base.items():
        retro = (k in ("Rahu", "Ketu")) or (k == "Mercury" and mercury_retro)
        out[k] = GrahaTransit(key=k, longitude=(s - 1) * 30.0 + 15.0, sign=s, retrograde=retro)
    return out


def _assert_calm_reasons(signals):
    for sig in signals:
        low = sig.reason.lower()
        for word in BANNED_WORDS:
            assert word not in low, f"Banned word {word!r} in {sig.id}: {sig.reason}"


def test_chandra_bala_all_houses():
    natal = NatalContext(moon_sign=4)  # Cancer
    for moon_sign in range(1, 13):
        ctx = DayContext(date(2025, 6, 10), _make_panchang(), _make_transits({"Moon": moon_sign}))
        sigs = evaluate_signals(ctx, natal)
        _assert_calm_reasons(sigs)
        house = house_from(moon_sign, natal.moon_sign)
        expected_id = "chandra_bala_good" if house in {1, 3, 6, 7, 10, 11} else "chandra_bala_poor"
        cb = [s for s in sigs if s.id.startswith("chandra_bala_")]
        assert len(cb) == 1
        assert cb[0].id == expected_id
        assert cb[0].params["house"] == house


def test_tara_bala_all_27_counts_and_wraparound():
    expected_cycle = [
        "tara_janma", "tara_sampat", "tara_vipat", "tara_kshema",
        "tara_pratyak", "tara_sadhana", "tara_naidhana", "tara_mitra", "tara_parama_mitra",
    ]
    # Natal nakshatra 25 guarantees wrap-around across 27 -> 1 for counts 1..27.
    natal = NatalContext(moon_sign=1, moon_nakshatra=25)
    for offset in range(27):
        today_nak = (25 - 1 + offset) % 27 + 1
        ctx = DayContext(date(2025, 6, 10), _make_panchang(nak_num=today_nak), _make_transits())
        sigs = evaluate_signals(ctx, natal)
        _assert_calm_reasons(sigs)
        tara_sigs = [s for s in sigs if s.id.startswith("tara_")]
        assert len(tara_sigs) == 1
        assert tara_sigs[0].id == expected_cycle[offset % 9]
        assert tara_sigs[0].params["count"] == offset + 1


def test_gochara_every_planet_and_house_both_ways():
    natal = NatalContext(moon_sign=3)  # Gemini
    for planet, good_houses in rules.GOCHARA_FAVOURABLE_HOUSES.items():
        if planet == "Moon":
            continue  # Moon is handled by Chandra Bala
        for sign in range(1, 13):
            ctx = DayContext(date(2025, 6, 10), _make_panchang(), _make_transits({planet: sign}))
            sigs = evaluate_signals(ctx, natal)
            _assert_calm_reasons(sigs)
            h = house_from(sign, natal.moon_sign)
            prefix = f"gochara_{planet.lower()}_"
            matched = [s for s in sigs if s.id.startswith(prefix)]
            assert len(matched) == 1
            expected = f"{prefix}good" if h in good_houses else f"{prefix}poor"
            assert matched[0].id == expected
            assert matched[0].params["house"] == h
            assert matched[0].kind == ("favourable" if h in good_houses else "unfavourable")
    # Ensure no gochara_moon_* signal is emitted.
    ctx = DayContext(date(2025, 6, 10), _make_panchang(), _make_transits())
    assert not any(s.id.startswith("gochara_moon_") for s in evaluate_signals(ctx, natal))


def test_saturn_cycles_all_12_signs():
    natal = NatalContext(moon_sign=10)  # Capricorn
    expected_by_house = {
        12: "sade_sati_rising",
        1: "sade_sati_peak",
        2: "sade_sati_setting",
        4: "kantaka_shani",
        8: "ashtama_shani",
    }
    for sat_sign in range(1, 13):
        ctx = DayContext(date(2025, 6, 10), _make_panchang(), _make_transits({"Saturn": sat_sign}))
        sigs = evaluate_signals(ctx, natal)
        _assert_calm_reasons(sigs)
        themes = [s for s in sigs if s.kind == "theme"]
        h = house_from(sat_sign, natal.moon_sign)
        if h in expected_by_house:
            assert [t.id for t in themes] == [expected_by_house[h]]
        else:
            assert themes == []


def test_rikta_tithis_and_amavasya():
    for num, should_fire in [
        (4, True), (9, True), (14, True),
        (19, True), (24, True), (29, True),
        (1, False), (10, False), (15, False),
    ]:
        ctx = DayContext(date(2025, 6, 10), _make_panchang(tithi_num=num), _make_transits())
        ids = {s.id for s in evaluate_signals(ctx, None)}
        assert ("rikta_tithi" in ids) is should_fire

    ctx_ama = DayContext(
        date(2025, 6, 10),
        _make_panchang(tithi_num=30, tithi_en="Amavasya", paksha="krishna"),
        _make_transits(),
    )
    ids_ama = {s.id for s in evaluate_signals(ctx_ama, None)}
    assert "amavasya" in ids_ama and "rikta_tithi" not in ids_ama


def test_vishti_karana_and_inauspicious_yogas_and_info_signals():
    ctx_bad = DayContext(
        date(2025, 6, 10),
        _make_panchang(karana_en="Vishti (Bhadra)", yoga_en="Vyatipata", vara_en="Wednesday"),
        _make_transits(mercury_retro=True),
    )
    sigs = evaluate_signals(ctx_bad, None)
    _assert_calm_reasons(sigs)
    ids = {s.id for s in sigs}
    assert {"vishti_karana", "inauspicious_yoga", "vara_wednesday", "mercury_retrograde"}.issubset(ids)

    ctx_ok = DayContext(
        date(2025, 6, 10),
        _make_panchang(karana_en="Bava", yoga_en="Siddhi", vara_en="Thursday"),
        _make_transits(mercury_retro=False),
    )
    ids_ok = {s.id for s in evaluate_signals(ctx_ok, None)}
    assert "vishti_karana" not in ids_ok
    assert "inauspicious_yoga" not in ids_ok
    assert "mercury_retrograde" not in ids_ok
    assert "vara_thursday" in ids_ok


def test_dasha_theme_reflects_natal_dignity_and_house():
    good_natal = NatalContext(
        moon_sign=2,
        moon_nakshatra=4,
        lagna_sign=1,
        running_dasha={"mahadasha": "Jupiter", "antardasha": "Venus"},
        planet_details={
            "Jupiter": {"dignity": "exalted", "house": 9, "sign": 4},
            "Venus": {"dignity": "own", "house": 5, "sign": 2},
        },
    )
    hard_natal = NatalContext(
        moon_sign=2,
        moon_nakshatra=4,
        lagna_sign=1,
        running_dasha={"mahadasha": "Jupiter", "antardasha": "Venus"},
        planet_details={
            "Jupiter": {"dignity": "debilitated", "house": 8, "sign": 10},
            "Venus": {"dignity": "debilitated", "house": 12, "sign": 6},
        },
    )
    ctx = DayContext(date(2025, 6, 10), _make_panchang(), _make_transits())
    good_dasha = next(s for s in evaluate_signals(ctx, good_natal) if s.id == "dasha_jupiter_venus")
    hard_dasha = next(s for s in evaluate_signals(ctx, hard_natal) if s.id == "dasha_jupiter_venus")
    assert sum(good_dasha.weights.values()) > sum(hard_dasha.weights.values())
    assert all(-2.0 <= v <= 2.0 for v in good_dasha.weights.values())
    assert all(-2.0 <= v <= 2.0 for v in hard_dasha.weights.values())


def test_nakshatra_and_tithi_tables_partition_exactly():
    # Nakshatra categories partition 1..27 cleanly.
    seen_nak: list[int] = []
    for _, _, nums, _ in rules.NAKSHATRA_CATEGORIES.values():
        seen_nak.extend(nums)
    assert len(seen_nak) == 27
    assert set(seen_nak) == set(range(1, 28))
    assert set(rules.NAKSHATRA_CATEGORY_BY_NUM.keys()) == set(range(1, 28))

    # Tithi categories cover 1..30 cleanly (1..29 via paksha number, 30 is Amavasya).
    seen_paksha: list[int] = []
    for _, _, nums, _ in rules.TITHI_CATEGORIES.values():
        seen_paksha.extend(nums)
    assert len(seen_paksha) == 15
    assert set(seen_paksha) == set(range(1, 16))
    for t in range(1, 30):
        assert ((t - 1) % 15 + 1) in rules.TITHI_SIGNAL_BY_PAKSHA_NUM


def test_special_days_fire_on_exact_tithis_only():
    expected = {
        11: "special_ekadashi",
        13: "special_pradosh",
        15: "special_purnima",
        19: "special_sankashti",
        26: "special_ekadashi",
        28: "special_pradosh",
    }
    for tithi_num in range(1, 31):
        ctx = DayContext(date(2025, 6, 10), _make_panchang(tithi_num=tithi_num), _make_transits())
        sigs = evaluate_signals(ctx, None)
        _assert_calm_reasons(sigs)
        specials = [s.id for s in sigs if s.id.startswith("special_")]
        if tithi_num in expected:
            assert specials == [expected[tithi_num]]
        else:
            assert specials == [], (tithi_num, specials)


def test_every_real_day_yields_one_nakshatra_one_tithi_and_vara_suits():
    tithi_family_ids = set(rules.TITHI_CATEGORIES.keys()) | {"amavasya"}
    for i in range(0, 365, 3):  # 122 real dates across 2025
        day = date(2025, 1, 1) + timedelta(days=i)
        rep = build_day_report(day, 28.6139, 77.2090, "Asia/Kolkata", None)
        _assert_calm_reasons(rep.signals)
        nak_sigs = [s for s in rep.signals if s.id.startswith("nakshatra_")]
        tithi_sigs = [s for s in rep.signals if s.id in tithi_family_ids]
        vara_sigs = [s for s in rep.signals if s.id.startswith("vara_")]
        assert len(nak_sigs) == 1
        assert len(tithi_sigs) == 1
        assert len(vara_sigs) == 1 and len(vara_sigs[0].params["suits"]) > 0
        assert all(s.scope == "daily" for s in nak_sigs + tithi_sigs + vara_sigs)
