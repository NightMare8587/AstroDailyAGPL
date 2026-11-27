"""Birth chart (kundli): lagna, nine grahas, whole-sign houses, Navamsa, Vimshottari dasha.

Sidereal, Lahiri ayanamsa. Houses are whole-sign (the sign of the lagna is house 1), which is the
classical Vedic default. Rahu is the mean node unless asked for the true node; Ketu is opposite.
"""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo

from . import dasha, ephem, names, zodiac

NAK_SPAN = 360.0 / 27

GRAHAS = [  # key, ephemeris body (None = lunar node handled separately)
    ("Sun", ephem.SUN), ("Moon", ephem.MOON), ("Mars", ephem.MARS), ("Mercury", ephem.MERCURY),
    ("Jupiter", ephem.JUPITER), ("Venus", ephem.VENUS), ("Saturn", ephem.SATURN),
]

INDIA_INDEPENDENCE = date(1947, 8, 15)


@dataclass
class BirthMoment:
    local: datetime       # timezone-aware, in the birth zone
    utc: datetime
    tz: tzinfo
    utc_offset_minutes: int
    warnings: list[str]


def resolve_birth_moment(day: date, clock: time, tz_name: str | None, utc_offset_minutes: int | None) -> BirthMoment:
    """Turn local birth date and time plus a zone (or an explicit UTC offset) into an exact moment."""
    warnings: list[str] = []
    naive = datetime.combine(day, clock.replace(tzinfo=None))
    if utc_offset_minutes is not None:
        tz: tzinfo = timezone(timedelta(minutes=utc_offset_minutes))
        local = naive.replace(tzinfo=tz)
    else:
        tz = ZoneInfo(tz_name or "Asia/Kolkata")
        local = naive.replace(tzinfo=tz)
        # A skipped hour (clocks forward) fails the round trip; a repeated hour (clocks back) round-trips
        # but has two possible offsets. Both are ambiguous for the user to confirm.
        if local.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None) != naive:
            warnings.append("This local time did not exist (clocks went forward); it was shifted. "
                            "Check the UTC offset.")
        elif local.replace(fold=0).utcoffset() != local.replace(fold=1).utcoffset():
            warnings.append("This local time happened twice (clocks went back); the first occurrence was used. "
                            "Check the UTC offset.")
        if day < INDIA_INDEPENDENCE:
            warnings.append("Births before 15 Aug 1947 may use a different local time standard "
                            "(local mean time, or wartime +06:30). Confirm the UTC offset.")
    utc = local.astimezone(timezone.utc)
    offset = local.utcoffset()
    return BirthMoment(local, utc, tz, int(offset.total_seconds() // 60) if offset else 0, warnings)


def _nakshatra(longitude: float) -> tuple[int, int]:
    """(nakshatra number 1..27, pada 1..4)."""
    idx = int(longitude // NAK_SPAN)
    pada = int((longitude - idx * NAK_SPAN) / (NAK_SPAN / 4)) + 1
    return idx + 1, min(pada, 4)


def _position(key: str, longitude: float, retrograde: bool, lagna_sign: int) -> dict:
    sign = zodiac.sign_of(longitude)
    nak, pada = _nakshatra(longitude)
    return {
        "key": key,
        "name": names_pair(zodiac.PLANET_NAMES[key]),
        "longitude": longitude,
        "sign": sign,
        "degree_in_sign": longitude - (sign - 1) * 30.0,
        "nakshatra": nak,
        "pada": pada,
        "house": (sign - lagna_sign) % 12 + 1,
        "retrograde": retrograde,
        "dignity": zodiac.dignity(key, sign),
        "navamsa_sign": zodiac.navamsa_sign(longitude),
    }


def names_pair(pair: tuple[str, str]) -> dict:
    return {"en": pair[0], "hi": pair[1]}


def compute_chart(birth: BirthMoment, lat: float, lon: float, node: str = "mean",
                  as_of: datetime | None = None) -> dict:
    jd = ephem.datetime_to_jd(birth.utc)
    asc = ephem.ascendant(jd, lat, lon)
    lagna_sign = zodiac.sign_of(asc)

    positions: list[dict] = []
    for key, body in GRAHAS:
        longitude, speed = ephem.body_position(jd, body)
        positions.append(_position(key, longitude, speed < 0, lagna_sign))
    rahu_lon, _ = ephem.body_position(jd, ephem.TRUE_NODE if node == "true" else ephem.MEAN_NODE)
    positions.append(_position("Rahu", rahu_lon, True, lagna_sign))  # nodes are always shown retrograde
    positions.append(_position("Ketu", (rahu_lon + 180.0) % 360.0, True, lagna_sign))

    nak, pada = _nakshatra(asc)
    lagna = {
        "longitude": asc, "sign": lagna_sign, "degree_in_sign": asc - (lagna_sign - 1) * 30.0,
        "nakshatra": nak, "pada": pada, "navamsa_sign": zodiac.navamsa_sign(asc),
    }

    houses = []
    for h in range(1, 13):
        sign = (lagna_sign + h - 2) % 12 + 1
        houses.append({"house": h, "sign": sign, "lord": zodiac.SIGN_LORDS[sign - 1],
                       "planets": [p["key"] for p in positions if p["house"] == h]})

    moon = next(p for p in positions if p["key"] == "Moon")
    balance, maha = dasha.mahadashas(moon["longitude"], birth.utc)
    moment = as_of or datetime.now(timezone.utc)

    def period(p: dasha.Period) -> dict:
        return {"lord": p.lord, "start": p.start.astimezone(birth.tz), "end": p.end.astimezone(birth.tz)}

    current = dasha.running(maha, moment)
    return {
        "ayanamsa": ephem.ayanamsa(jd),
        "lagna": lagna,
        "planets": positions,
        "houses": houses,
        "dasha": {
            "system": "vimshottari",
            "year_length_days": dasha.YEAR_DAYS,
            "balance_at_birth": {
                "lord": balance.lord, "years_total": balance.years_total,
                "fraction_elapsed": balance.fraction_elapsed, "years_remaining": balance.years_remaining,
            },
            "mahadashas": [
                {**period(m), "antardashas": [period(a) for a in dasha.subperiods(m)]} for m in maha
            ],
            "as_of": moment.astimezone(birth.tz),
            "current": {k: period(v) for k, v in current.items()} if current else None,
        },
    }
