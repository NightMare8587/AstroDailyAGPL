"""Tests for astrodaily.calc.transits (positions, house_from, next_ingress, sade_sati_state)."""
from datetime import date, datetime, timedelta, timezone

import pytest

from astrodaily.calc.transits import (
    ALL_GRAHAS,
    house_from,
    next_ingress,
    sade_sati_state,
    transit_positions,
)
from astrodaily.calc import ephem


# Independent verification note:
# Verified against ndastro-engine (Skyfield + JPL DE440, Lahiri ayanamsa) in the read-only
# xcheck venv:
#   - Saturn Aquarius (11) -> Pisces (12): 2025-03-29T16:04:52Z (sidereal lon = 330.000 deg)
#   - Jupiter Taurus (2) -> Gemini (3):   2025-05-14T17:01:16Z (sidereal lon =  60.000 deg)
#   - Rahu (mean node, node_type="mean") Pisces (12) -> Aquarius (11):
#                                         2025-05-18T14:23:23Z (sidereal lon = 330.000 deg)
#   - Retrograde re-entries:
#     * Mars Cancer (4) -> Gemini (3):    2025-01-21T04:38:10Z
#     * Mercury Scorpio (8) -> Libra (7): 2025-11-23T14:39:09Z
#     * Jupiter Cancer (4) -> Gemini (3): 2025-12-05T12:28:40Z
VERIFIED_INGRESSES = [
    ("Saturn", datetime(2025, 3, 15, tzinfo=timezone.utc), 30.0, date(2025, 3, 29), 11, 12),
    ("Jupiter", datetime(2025, 5, 1, tzinfo=timezone.utc), 30.0, date(2025, 5, 14), 2, 3),
    ("Rahu", datetime(2025, 5, 1, tzinfo=timezone.utc), 30.0, date(2025, 5, 18), 12, 11),
]


@pytest.mark.parametrize(
    ("key", "start", "window_days", "expected_date", "from_sign", "to_sign"),
    VERIFIED_INGRESSES,
    ids=["saturn_2025", "jupiter_2025", "rahu_mean_2025"],
)
def test_verified_ingress_vectors(key, start, window_days, expected_date, from_sign, to_sign):
    ing = next_ingress(key, after=start, within_days=window_days)
    assert ing is not None
    assert ing.key == key
    assert ing.from_sign == from_sign
    assert ing.to_sign == to_sign
    assert ing.when.tzinfo == timezone.utc
    assert abs((ing.when.date() - expected_date).days) <= 1
    assert ing.when.date() == expected_date


@pytest.mark.parametrize(
    ("key", "start", "expected_date", "from_sign", "to_sign"),
    [
        ("Mars", datetime(2025, 1, 10, tzinfo=timezone.utc), date(2025, 1, 21), 4, 3),
        ("Mercury", datetime(2025, 11, 15, tzinfo=timezone.utc), date(2025, 11, 23), 8, 7),
        ("Jupiter", datetime(2025, 11, 20, tzinfo=timezone.utc), date(2025, 12, 5), 4, 3),
    ],
    ids=["mars_retro_reentry", "mercury_retro_reentry", "jupiter_retro_reentry"],
)
def test_next_ingress_handles_retrograde_reentry(key, start, expected_date, from_sign, to_sign):
    ing = next_ingress(key, after=start, within_days=30.0)
    assert ing is not None
    assert ing.from_sign == from_sign
    assert ing.to_sign == to_sign
    assert abs((ing.when.date() - expected_date).days) <= 1
    # Retrograde flag at ingress instant should be True (except mean node is always True).
    jd = ephem.datetime_to_jd(ing.when)
    assert transit_positions(jd)[key].retrograde is True


def test_next_ingress_monotonic_and_window_bounds():
    start = datetime(2025, 3, 1, tzinfo=timezone.utc)
    # Moon crosses multiple signs in a month; repeated calls from each ingress.when advance strictly.
    seen_times = []
    cursor = start
    for _ in range(4):
        ing = next_ingress("Moon", after=cursor, within_days=10.0)
        assert ing is not None
        assert ing.when > cursor
        seen_times.append(ing.when)
        cursor = ing.when
    assert seen_times == sorted(seen_times)
    # Saturn does not change sign in 5 days starting 2025-03-01.
    assert next_ingress("Saturn", after=start, within_days=5.0) is None
    assert next_ingress("Saturn", after=start, within_days=0.0) is None


def test_transit_positions_invariants():
    jd = ephem.datetime_to_jd(datetime(2025, 5, 14, 12, 0, tzinfo=timezone.utc))
    pos = transit_positions(jd)
    assert tuple(pos.keys()) == ALL_GRAHAS
    for key, tr in pos.items():
        assert tr.key == key
        assert 0.0 <= tr.longitude < 360.0
        assert tr.sign == int(tr.longitude // 30.0) + 1
    assert pos["Rahu"].retrograde is True and pos["Ketu"].retrograde is True
    assert not pos["Sun"].retrograde and not pos["Moon"].retrograde
    diff = abs((pos["Ketu"].longitude - pos["Rahu"].longitude + 180.0) % 360.0 - 180.0)
    assert diff == pytest.approx(180.0, abs=1e-9)


def test_house_from_all_wraps():
    assert house_from(1, 1) == 1
    assert house_from(12, 1) == 12
    assert house_from(1, 12) == 2
    assert house_from(5, 9) == 9
    for ref in range(1, 13):
        houses = [house_from(s, ref) for s in range(1, 13)]
        assert sorted(houses) == list(range(1, 13))
        assert house_from(ref, ref) == 1


def test_sade_sati_state_all_twelve_saturn_signs():
    moon_sign = 5  # Leo
    expected_by_house = {
        12: "rising",
        1: "peak",
        2: "setting",
        4: "kantaka",
        8: "ashtama",
    }
    for saturn_sign in range(1, 13):
        h = house_from(saturn_sign, moon_sign)
        assert sade_sati_state(moon_sign, saturn_sign) == expected_by_house.get(h)
