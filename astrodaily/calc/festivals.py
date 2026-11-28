"""Hindu festival dates for a place, worked out from the Sun and Moon.

A festival is defined by a lunar month, a paksha and a tithi number, plus the part of the day (kala) that the
tithi must cover. This follows the usual rule of the almanacs: the day whose chosen moment falls inside the
tithi. Months are counted from new moon to new moon (amanta), named by the sign the Sun is in at the start:
Sun in Pisces at new moon -> Chaitra, in Aries -> Vaishakha, and so on. A month with no sankranti is the extra
(adhika) month and is skipped, since festivals belong to the regular month.

Draft: the festival list, the kala for each and the tie rules are conventions that need a panchang reviewer.
Regional practice differs (purnimanta names, Smarta and Vaishnava dates for Janmashtami and Ekadashi).
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from . import ephem, zodiac
from .panchang import _karana_index, _moon_sun_diff, _tithi_index

SYNODIC = 29.530588  # mean days from new moon to new moon
MOON_MEAN_RATE = 360.0 / SYNODIC  # degrees of Moon-Sun separation per day


@dataclass(frozen=True)
class Spec:
    key: str
    en: str
    hi: str
    month: int   # 1 Chaitra .. 12 Phalguna (amanta)
    paksha: str  # "shukla" or "krishna"
    tithi: int   # 1..15 inside the paksha (15 = Purnima or Amavasya)
    kala: str    # sunrise, purvahna, madhyahna, aparahna, pradosh, nishita
    tie: str = "first"  # when the tithi covers the kala on two days running: the "first" day or the "last"
    bhadra: bool = False  # not kept while Bhadra (Vishti karana) runs at the kala


FESTIVALS: tuple[Spec, ...] = (
    Spec("ugadi", "Ugadi / Gudi Padwa", "उगादी / गुड़ी पड़वा", 1, "shukla", 1, "sunrise"),
    Spec("chaitra_navratri", "Chaitra Navratri begins", "चैत्र नवरात्रि आरंभ", 1, "shukla", 1, "sunrise"),
    Spec("ram_navami", "Ram Navami", "राम नवमी", 1, "shukla", 9, "madhyahna"),
    Spec("hanuman_jayanti", "Hanuman Jayanti", "हनुमान जयंती", 1, "shukla", 15, "sunrise"),
    Spec("akshaya_tritiya", "Akshaya Tritiya", "अक्षय तृतीया", 2, "shukla", 3, "purvahna"),
    Spec("buddha_purnima", "Buddha Purnima", "बुद्ध पूर्णिमा", 2, "shukla", 15, "sunrise"),
    Spec("rath_yatra", "Rath Yatra", "रथ यात्रा", 4, "shukla", 2, "sunrise"),
    Spec("guru_purnima", "Guru Purnima", "गुरु पूर्णिमा", 4, "shukla", 15, "sunrise"),
    Spec("nag_panchami", "Nag Panchami", "नाग पंचमी", 5, "shukla", 5, "sunrise"),
    Spec("raksha_bandhan", "Raksha Bandhan", "रक्षा बंधन", 5, "shukla", 15, "aparahna", bhadra=True),
    Spec("hartalika_teej", "Hartalika Teej", "हरतालिका तीज", 6, "shukla", 3, "sunrise"),
    Spec("ganesh_chaturthi", "Ganesh Chaturthi", "गणेश चतुर्थी", 6, "shukla", 4, "madhyahna"),
    Spec("sharad_navratri", "Sharad Navratri begins", "शारदीय नवरात्रि आरंभ", 7, "shukla", 1, "sunrise"),
    Spec("durga_ashtami", "Durga Ashtami", "दुर्गा अष्टमी", 7, "shukla", 8, "sunrise"),
    Spec("maha_navami", "Maha Navami", "महानवमी", 7, "shukla", 9, "aparahna"),
    Spec("dussehra", "Dussehra (Vijayadashami)", "दशहरा (विजयादशमी)", 7, "shukla", 10, "aparahna"),
    Spec("karwa_chauth", "Karwa Chauth", "करवा चौथ", 7, "krishna", 4, "pradosh"),
    Spec("dhanteras", "Dhanteras", "धनतेरस", 7, "krishna", 13, "pradosh"),
    Spec("diwali", "Diwali (Lakshmi Puja)", "दिवाली (लक्ष्मी पूजा)", 7, "krishna", 15, "pradosh", tie="last"),
    Spec("govardhan", "Govardhan Puja", "गोवर्धन पूजा", 8, "shukla", 1, "sunrise"),
    Spec("bhai_dooj", "Bhai Dooj", "भाई दूज", 8, "shukla", 2, "sunrise"),
    Spec("chhath", "Chhath Puja (main day)", "छठ पूजा (मुख्य दिन)", 8, "shukla", 6, "pradosh"),
    Spec("kartik_purnima", "Kartik Purnima", "कार्तिक पूर्णिमा", 8, "shukla", 15, "sunrise"),
    Spec("vasant_panchami", "Vasant Panchami", "वसंत पंचमी", 11, "shukla", 5, "purvahna"),
    Spec("mahashivratri", "Maha Shivaratri", "महाशिवरात्रि", 11, "krishna", 14, "nishita"),
)
SANKRANTI = ("makar_sankranti", "Makar Sankranti", "मकर संक्रांति")


@dataclass(frozen=True)
class Festival:
    key: str
    en: str
    hi: str


@dataclass(frozen=True)
class _LunarMonth:
    start: float  # Julian day of the new moon that starts it
    end: float
    number: int   # 1..12
    adhika: bool


def _new_moon_near(jd: float) -> float:
    """The new moon (Moon-Sun separation 0) closest to ``jd``, by Newton steps on the mean rate."""
    t = jd
    for _ in range(8):
        d = _moon_sun_diff(t)
        if d > 180.0:
            d -= 360.0
        t -= d / MOON_MEAN_RATE
    return t


def _month_at(jd: float) -> _LunarMonth:
    d = _moon_sun_diff(jd)
    start = _new_moon_near(jd - d / MOON_MEAN_RATE)
    end = _new_moon_near(start + SYNODIC)
    sign_start = zodiac.sign_of(ephem.sidereal_longitude(start + 0.01, ephem.SUN))
    sign_end = zodiac.sign_of(ephem.sidereal_longitude(end + 0.01, ephem.SUN))
    return _LunarMonth(start, end, sign_start % 12 + 1, sign_start == sign_end)


class _Months:
    """Lunar months looked up by moment, each worked out once."""

    def __init__(self) -> None:
        self._known: list[_LunarMonth] = []

    def at(self, jd: float) -> _LunarMonth:
        for m in self._known:
            if m.start <= jd < m.end:
                return m
        m = _month_at(jd)
        self._known.append(m)
        return m


def _kala_moment(kala: str, sunrise: datetime, sunset: datetime, next_sunrise: datetime) -> datetime:
    day = sunset - sunrise
    return {
        "sunrise": sunrise,
        "purvahna": sunrise + day * 0.25,
        "madhyahna": sunrise + day * 0.5,
        "aparahna": sunrise + day * 0.7,
        "pradosh": sunset + timedelta(minutes=36),
        "nishita": sunset + (next_sunrise - sunset) / 2,
    }[kala]


def _is_vishti(jd: float) -> bool:
    k = _karana_index(jd)  # 0..59; the movable karanas fill 1..56 and Vishti is every seventh
    return 1 <= k <= 56 and (k - 1) % 7 == 6


def _jd(dt: datetime) -> float:
    return ephem.datetime_to_jd(dt)


def festival_days(first: date, last: date, lat: float, lon: float, tz_name: str) -> dict[date, list[Festival]]:
    """Festivals falling on each local day from ``first`` to ``last`` (both included)."""
    tz = ZoneInfo(tz_name)
    months = _Months()
    # Look one day each way: a festival lands on the first day its tithi covers the kala.
    start = first - timedelta(days=2)
    days: list[date] = [start + timedelta(days=n) for n in range((last - start).days + 2)]

    moments: dict[date, tuple[datetime, datetime, datetime]] = {}
    for day in days:
        midnight = datetime(day.year, day.month, day.day, tzinfo=tz)
        jd_rise = ephem.next_sunrise(ephem.datetime_to_jd(midnight), lat, lon)
        jd_set = ephem.next_sunset(jd_rise, lat, lon)
        jd_next = ephem.next_sunrise(jd_set, lat, lon)
        moments[day] = (ephem.jd_to_datetime(jd_rise, tz), ephem.jd_to_datetime(jd_set, tz),
                        ephem.jd_to_datetime(jd_next, tz))

    def covers(spec: Spec, day: date) -> bool:
        sunrise, sunset, next_sunrise = moments[day]
        jd = _jd(_kala_moment(spec.kala, sunrise, sunset, next_sunrise))
        month = months.at(jd)
        want = (0 if spec.paksha == "shukla" else 15) + spec.tithi - 1
        if not (month.number == spec.month and not month.adhika and _tithi_index(jd) == want):
            return False
        return not (spec.bhadra and _is_vishti(jd))

    def at_any_point(spec: Spec, day: date) -> bool:
        """The tithi is missing at the kala (a skipped tithi) but still occurs during this day."""
        sunrise, sunset, next_sunrise = moments[day]
        want = (0 if spec.paksha == "shukla" else 15) + spec.tithi - 1
        for moment in (sunrise, sunset, next_sunrise):
            jd = _jd(moment)
            month = months.at(jd)
            if month.number == spec.month and not month.adhika and _tithi_index(jd) == want:
                return True
        return False

    found: dict[str, list[date]] = {}
    for spec in FESTIVALS:
        hits = [d for d in days[1:-1] if covers(spec, d)]
        # A tithi can cover the kala on two days running; the first day is the one observed.
        if spec.tie == "last":
            hits = [d for d in hits if (d + timedelta(days=1)) not in hits]
        else:
            hits = [d for d in hits if (d - timedelta(days=1)) not in hits]
        if not hits and spec.bhadra:
            # Bhadra ruled out the first day and the tithi is over by the next one: the next evening is used.
            first_day = [d for d in days[1:-1] if at_any_point(spec, d)][:1]
            hits = [first_day[0] + timedelta(days=1)] if first_day and _is_vishti(
                _jd(_kala_moment(spec.kala, *moments[first_day[0]]))) else first_day
        if not hits:
            hits = [d for d in days[1:-1] if at_any_point(spec, d)][:1]
        found[spec.key] = hits

    out: dict[date, list[Festival]] = {}

    def add(day: date, key: str, en: str, hi: str) -> None:
        if first <= day <= last:
            out.setdefault(day, []).append(Festival(key, en, hi))

    for spec in FESTIVALS:
        for day in found[spec.key]:
            add(day, spec.key, spec.en, spec.hi)

    # Makar Sankranti: the Sun enters sidereal Capricorn (sign 10). After sunset it is observed next day.
    jd_a = ephem.datetime_to_jd(datetime(first.year, first.month, first.day, tzinfo=tz)) - 1.0
    jd_b = ephem.datetime_to_jd(datetime(last.year, last.month, last.day, tzinfo=tz)) + 2.0
    t = jd_a
    while t < jd_b:
        if zodiac.sign_of(ephem.sidereal_longitude(t, ephem.SUN)) != zodiac.sign_of(
                ephem.sidereal_longitude(t + 0.25, ephem.SUN)) and zodiac.sign_of(
                ephem.sidereal_longitude(t + 0.25, ephem.SUN)) == 10:
            lo, hi = t, t + 0.25
            for _ in range(30):
                mid = (lo + hi) / 2
                if zodiac.sign_of(ephem.sidereal_longitude(mid, ephem.SUN)) == 10:
                    hi = mid
                else:
                    lo = mid
            moment = ephem.jd_to_datetime(hi, tz)
            day = moment.date()
            sunset = moments.get(day, (None, None, None))[1]
            if sunset is not None and moment > sunset:
                day += timedelta(days=1)
            add(day, *SANKRANTI)
        t += 0.25
    return out
