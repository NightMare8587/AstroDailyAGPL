"""Vimshottari dasha (120-year cycle), from the Moon's sidereal longitude at birth.

Pure functions, no ephemeris. A year is 365.25 days (the common convention in Jyotish software;
some sources use 360 or 365.2563 days, which shifts dates by a few days over a lifetime).
"""
from dataclasses import dataclass
from datetime import datetime, timedelta

ORDER = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
YEARS = {"Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
         "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17}
CYCLE_YEARS = 120
YEAR_DAYS = 365.25
NAKSHATRA_SPAN = 360.0 / 27


@dataclass
class Period:
    lord: str
    start: datetime
    end: datetime


@dataclass
class Balance:
    lord: str
    years_total: int
    fraction_elapsed: float  # how much of the Moon's nakshatra had passed at birth
    years_remaining: float


def nakshatra_lord(nakshatra_index: int) -> str:
    """Lord of nakshatra 0..26 (Ashwini = Ketu, Bharani = Venus, ... repeating every nine)."""
    return ORDER[nakshatra_index % 9]


def mahadashas(moon_longitude: float, birth: datetime) -> tuple[Balance, list[Period]]:
    """The nine mahadashas. The first started before birth; its elapsed part is the unlived balance."""
    moon_longitude %= 360.0
    nak = int(moon_longitude // NAKSHATRA_SPAN)
    fraction = (moon_longitude - nak * NAKSHATRA_SPAN) / NAKSHATRA_SPAN
    lord = nakshatra_lord(nak)
    years = YEARS[lord]
    balance = Balance(lord, years, fraction, years * (1 - fraction))
    start = birth - timedelta(days=years * fraction * YEAR_DAYS)
    first = ORDER.index(lord)
    periods: list[Period] = []
    t = start
    for k in range(9):
        lord_k = ORDER[(first + k) % 9]
        end = t + timedelta(days=YEARS[lord_k] * YEAR_DAYS)
        periods.append(Period(lord_k, t, end))
        t = end
    return balance, periods


def subperiods(parent: Period) -> list[Period]:
    """Antardashas of a mahadasha, or pratyantardashas of an antardasha: nine parts proportional
    to the lords' years, starting with the parent's own lord."""
    total = parent.end - parent.start
    first = ORDER.index(parent.lord)
    out: list[Period] = []
    cumulative = 0
    t = parent.start
    for k in range(9):
        lord_k = ORDER[(first + k) % 9]
        cumulative += YEARS[lord_k]
        end = parent.end if k == 8 else parent.start + total * cumulative / CYCLE_YEARS
        out.append(Period(lord_k, t, end))
        t = end
    return out


def find(periods: list[Period], moment: datetime) -> Period | None:
    for p in periods:
        if p.start <= moment < p.end:
            return p
    return None


def running(periods: list[Period], moment: datetime) -> dict[str, Period] | None:
    """The mahadasha, antardasha and pratyantardasha running at `moment`, or None if outside the cycle."""
    maha = find(periods, moment)
    if maha is None:
        return None
    antar = find(subperiods(maha), moment)
    pratyantar = find(subperiods(antar), moment)
    return {"mahadasha": maha, "antardasha": antar, "pratyantardasha": pratyantar}
