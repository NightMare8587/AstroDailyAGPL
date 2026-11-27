"""Daily panchang and muhurat for a date and place (all times local to the given tz)."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from . import ephem, names

NAK_SPAN = 360.0 / 27  # 13 deg 20 min

# Weekday -> which 1/8th of the daytime is Rahu Kaal, Gulika, Yamaganda (Sunday first).
RAHU_SEGMENT = [8, 2, 7, 5, 6, 4, 3]
GULIKA_SEGMENT = [7, 6, 5, 4, 3, 2, 1]
YAMAGANDA_SEGMENT = [4, 3, 2, 1, 7, 6, 5]


@dataclass
class Span:
    en: str
    hi: str
    start: datetime
    end: datetime
    nature: str | None = None


@dataclass
class Element:
    """A panchang element active at sunrise, with the time it ends."""
    number: int
    en: str
    hi: str
    ends_at: datetime
    extra: dict


def _moon_sun_diff(jd: float) -> float:
    return (ephem.sidereal_longitude(jd, ephem.MOON) - ephem.sidereal_longitude(jd, ephem.SUN)) % 360.0


def _tithi_index(jd: float) -> int:  # 0..29
    return int(_moon_sun_diff(jd) / 12.0)


def _karana_index(jd: float) -> int:  # 0..59
    return int(_moon_sun_diff(jd) / 6.0)


def _nakshatra_index(jd: float) -> int:  # 0..26
    return int(ephem.sidereal_longitude(jd, ephem.MOON) / NAK_SPAN)


def _yoga_index(jd: float) -> int:  # 0..26
    total = (ephem.sidereal_longitude(jd, ephem.SUN) + ephem.sidereal_longitude(jd, ephem.MOON)) % 360.0
    return int(total / NAK_SPAN)


def _find_change(index_fn, jd_start: float, max_days: float = 3.0) -> float:
    """Julian day (UT) at which index_fn(jd) first differs from its value at jd_start."""
    start_value = index_fn(jd_start)
    step = 1.0 / 48.0  # 30 minutes; shorter than any element's duration
    lo = jd_start
    hi = jd_start + step
    limit = jd_start + max_days
    while index_fn(hi) == start_value:
        lo = hi
        hi += step
        if hi > limit:
            raise ValueError("element did not change within search window")
    for _ in range(40):  # ~ sub-second precision
        mid = (lo + hi) / 2.0
        if index_fn(mid) == start_value:
            lo = mid
        else:
            hi = mid
    return hi


def tithi_name(index: int) -> tuple[str, str, str]:
    """(english, hindi, paksha key) for a 0..29 tithi index."""
    paksha = "shukla" if index < 15 else "krishna"
    n = index % 15
    if n == 14:
        en, hi = names.PURNIMA if paksha == "shukla" else names.AMAVASYA
    else:
        en, hi = names.TITHI[n]
    return en, hi, paksha


def karana_name(index: int) -> tuple[str, str]:
    if index in names.KARANA_FIXED:
        return names.KARANA_FIXED[index]
    return names.KARANA_MOVABLE[(index - 1) % 7]


def split_segments(start: datetime, end: datetime, parts: int) -> list[tuple[datetime, datetime]]:
    length = (end - start) / parts
    return [(start + length * i, start + length * (i + 1)) for i in range(parts)]


def choghadiya_slots(vara: int, sunrise: datetime, sunset: datetime, next_sunrise: datetime) -> list[Span]:
    day_start = names.CHOGHADIYA_DAY_START[vara]
    night_start = (day_start + 5) % 7
    out: list[Span] = []
    # Day slots step forward one place in the cycle; night slots step back two places.
    for first, step, (a, b) in (
        (day_start, 1, (sunrise, sunset)),
        (night_start, -2, (sunset, next_sunrise)),
    ):
        for i, (s, e) in enumerate(split_segments(a, b, 8)):
            en, hi, nature = names.CHOGHADIYA_CYCLE[(first + step * i) % 7]
            out.append(Span(en, hi, s, e, nature))
    return out


def compute_panchang(day: date, lat: float, lon: float, tz_name: str) -> dict:
    tz = ZoneInfo(tz_name)
    midnight = datetime(day.year, day.month, day.day, tzinfo=tz)
    jd_mid = ephem.datetime_to_jd(midnight)

    jd_rise = ephem.next_sunrise(jd_mid, lat, lon)
    jd_set = ephem.next_sunset(jd_rise, lat, lon)
    jd_next_rise = ephem.next_sunrise(jd_set, lat, lon)
    sunrise = ephem.jd_to_datetime(jd_rise, tz)
    sunset = ephem.jd_to_datetime(jd_set, tz)
    next_sunrise = ephem.jd_to_datetime(jd_next_rise, tz)

    vara = (day.weekday() + 1) % 7  # Sunday = 0

    t_idx = _tithi_index(jd_rise)
    t_en, t_hi, paksha = tithi_name(t_idx)
    tithi = Element(t_idx + 1, t_en, t_hi, ephem.jd_to_datetime(_find_change(_tithi_index, jd_rise), tz),
                    {"paksha": paksha})

    n_idx = _nakshatra_index(jd_rise)
    moon_lon = ephem.sidereal_longitude(jd_rise, ephem.MOON)
    pada = int((moon_lon % NAK_SPAN) / (NAK_SPAN / 4)) + 1
    nakshatra = Element(n_idx + 1, *names.NAKSHATRA[n_idx],
                        ephem.jd_to_datetime(_find_change(_nakshatra_index, jd_rise), tz), {"pada": pada})

    y_idx = _yoga_index(jd_rise)
    yoga = Element(y_idx + 1, *names.YOGA[y_idx],
                   ephem.jd_to_datetime(_find_change(_yoga_index, jd_rise), tz), {})

    k_idx = _karana_index(jd_rise)
    karana = Element(k_idx + 1, *karana_name(k_idx),
                     ephem.jd_to_datetime(_find_change(_karana_index, jd_rise), tz), {})

    segs = split_segments(sunrise, sunset, 8)

    def seg(table, label) -> Span:
        s, e = segs[table[vara] - 1]
        return Span(label[0], label[1], s, e)

    muhurta = (sunset - sunrise) / 15
    abhijit = Span(*names.ABHIJIT, sunrise + muhurta * 7, sunrise + muhurta * 8)

    return {
        "date": day,
        "timezone": tz_name,
        "sunrise": sunrise,
        "sunset": sunset,
        "next_sunrise": next_sunrise,
        "vara": names.VARA[vara],
        "tithi": tithi,
        "nakshatra": nakshatra,
        "yoga": yoga,
        "karana": karana,
        "rahu_kaal": seg(RAHU_SEGMENT, names.RAHU_KAAL),
        "gulika_kaal": seg(GULIKA_SEGMENT, names.GULIKA),
        "yamaganda": seg(YAMAGANDA_SEGMENT, names.YAMAGANDA),
        "abhijit": abhijit,
        "choghadiya": choghadiya_slots(vara, sunrise, sunset, next_sunrise),
        "ayanamsa": ephem.ayanamsa(jd_rise),
    }
