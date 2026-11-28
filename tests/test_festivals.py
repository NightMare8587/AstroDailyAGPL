"""Festival dates. The expected 2026 dates are Drik Panchang's list for New Delhi (read 2026-11-28)."""
from datetime import date

from astrodaily.calc import festivals

DELHI = (28.6139, 77.2090, "Asia/Kolkata")

DRIK_2026 = {
    "makar_sankranti": date(2026, 1, 14), "vasant_panchami": date(2026, 1, 23), "mahashivratri": date(2026, 2, 15),
    "ugadi": date(2026, 3, 19), "chaitra_navratri": date(2026, 3, 19), "ram_navami": date(2026, 3, 26),
    "hanuman_jayanti": date(2026, 4, 2), "akshaya_tritiya": date(2026, 4, 19), "buddha_purnima": date(2026, 5, 1),
    "rath_yatra": date(2026, 7, 16), "guru_purnima": date(2026, 7, 29), "nag_panchami": date(2026, 8, 17),
    "raksha_bandhan": date(2026, 8, 28), "hartalika_teej": date(2026, 9, 14), "ganesh_chaturthi": date(2026, 9, 14),
    "sharad_navratri": date(2026, 10, 11), "durga_ashtami": date(2026, 10, 19), "maha_navami": date(2026, 10, 19),
    "dussehra": date(2026, 10, 20), "karwa_chauth": date(2026, 10, 29), "dhanteras": date(2026, 11, 6),
    "diwali": date(2026, 11, 8), "govardhan": date(2026, 11, 10), "bhai_dooj": date(2026, 11, 11),
    "chhath": date(2026, 11, 15), "kartik_purnima": date(2026, 11, 24),
}


def _year(year: int) -> dict[str, date]:
    out = {}
    for day, found in festivals.festival_days(date(year, 1, 1), date(year, 12, 31), *DELHI).items():
        for f in found:
            out[f.key] = day
    return out


def test_2026_matches_the_published_list():
    assert _year(2026) == DRIK_2026


def test_diwali_takes_the_second_day_when_the_new_moon_covers_the_evening_twice():
    assert _year(2024)["diwali"] == date(2024, 11, 1)


def test_raksha_bandhan_waits_out_bhadra():
    assert _year(2026)["raksha_bandhan"] == date(2026, 8, 28)  # Purnima began on the 27th but Bhadra ran through the afternoon


def test_extra_month_is_skipped():
    # 2026 has an extra Jyeshtha (17 May to 15 June); Rath Yatra belongs to the following Ashadha.
    assert _year(2026)["rath_yatra"] == date(2026, 7, 16)


def test_a_month_range_returns_only_its_days():
    out = festivals.festival_days(date(2026, 11, 1), date(2026, 11, 30), *DELHI)
    assert min(out) >= date(2026, 11, 1) and max(out) <= date(2026, 11, 30)
    assert [f.key for f in out[date(2026, 11, 8)]] == ["diwali"]
    f = out[date(2026, 11, 8)][0]
    assert f.en and f.hi
