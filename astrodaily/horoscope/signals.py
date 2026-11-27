"""Rule evaluation: turns DayContext and optional NatalContext into Signal instances."""
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal

from astrodaily.calc import zodiac
from astrodaily.calc.transits import GrahaTransit, house_from, next_ingress, sade_sati_state
from . import rules, weights

SignalKind = Literal["favourable", "unfavourable", "theme", "coming_up", "info"]
SignalScope = Literal["daily", "standing"]


@dataclass(frozen=True)
class Signal:
    id: str
    params: dict[str, Any]
    weights: dict[str, float]
    reason: str
    kind: SignalKind
    scope: SignalScope = "daily"


@dataclass(frozen=True)
class DayContext:
    date: date
    panchang: dict[str, Any]
    transits: dict[str, GrahaTransit]


@dataclass(frozen=True)
class NatalContext:
    moon_sign: int
    moon_nakshatra: int | None = None
    lagna_sign: int | None = None
    running_dasha: dict[str, str] | None = None
    planet_details: dict[str, dict[str, Any]] | None = None


def _weights_for(key: str) -> dict[str, float]:
    row = weights.WEIGHTS[key]
    return {area: float(row[area]) for area in weights.AREAS}


def _find_running_dasha(mahadashas: list[dict[str, Any]], as_of: datetime) -> dict[str, str] | None:
    for maha in mahadashas:
        if maha["start"] <= as_of < maha["end"]:
            for antar in maha.get("antardashas", ()):
                if antar["start"] <= as_of < antar["end"]:
                    return {"mahadasha": maha["lord"], "antardasha": antar["lord"]}
            return {"mahadasha": maha["lord"], "antardasha": maha["lord"]}
    return None


def natal_from_chart(chart: dict[str, Any], as_of: datetime | None = None) -> NatalContext:
    """Build a Level B NatalContext from a ``compute_chart`` dictionary."""
    planets = chart["planets"]
    moon = next(p for p in planets if p["key"] == "Moon")
    planet_details = {
        p["key"]: {"house": p["house"], "dignity": p["dignity"], "sign": p["sign"]}
        for p in planets
    }

    dasha_info = chart.get("dasha") or {}
    running_dasha: dict[str, str] | None = None
    if as_of is not None:
        mahadashas = dasha_info.get("mahadashas") or []
        if as_of.tzinfo is None and mahadashas:
            as_of = as_of.replace(tzinfo=mahadashas[0]["start"].tzinfo)
        running_dasha = _find_running_dasha(mahadashas, as_of)
    else:
        current = dasha_info.get("current")
        if current and "mahadasha" in current and "antardasha" in current:
            running_dasha = {
                "mahadasha": current["mahadasha"]["lord"],
                "antardasha": current["antardasha"]["lord"],
            }

    return NatalContext(
        moon_sign=int(moon["sign"]),
        moon_nakshatra=int(moon["nakshatra"]),
        lagna_sign=int(chart["lagna"]["sign"]),
        running_dasha=running_dasha,
        planet_details=planet_details,
    )


def _chandra_bala_signals(day: DayContext, natal: NatalContext) -> list[Signal]:
    moon_sign = day.transits["Moon"].sign
    house = house_from(moon_sign, natal.moon_sign)
    if house in rules.CHANDRA_BALA_GOOD_HOUSES:
        return [Signal(
            id="chandra_bala_good",
            params={"house": house, "moon_sign": moon_sign},
            weights=_weights_for("chandra_bala_good"),
            reason=f"Moon in house {house} from natal Moon supports steady progress and calm focus.",
            kind="favourable",
        )]
    return [Signal(
        id="chandra_bala_poor",
        params={"house": house, "moon_sign": moon_sign},
        weights=_weights_for("chandra_bala_poor"),
        reason=f"Moon in house {house} from natal Moon invites a measured pace and routine tasks.",
        kind="unfavourable",
    )]


def _tara_bala_signals(day: DayContext, natal: NatalContext) -> list[Signal]:
    if natal.moon_nakshatra is None:
        return []
    today_nak = int(day.panchang["nakshatra"].number)
    count = (today_nak - natal.moon_nakshatra) % 27 + 1
    tara = (count - 1) % 9 + 1
    slug, label, kind = rules.TARA_TABLE[tara]
    sig_id = f"tara_{slug}"
    if kind == "favourable":
        reason = f"{label} tara (count {count} from birth nakshatra) favours constructive effort."
    elif tara == 1:
        reason = f"Janma tara (count {count} from birth nakshatra) asks for moderation and self-care."
    else:
        reason = f"{label} tara (count {count} from birth nakshatra) suggests sticking to familiar routines."
    return [Signal(
        id=sig_id,
        params={"tara": tara, "tara_name": label, "count": count, "nakshatra": today_nak},
        weights=_weights_for(sig_id),
        reason=reason,
        kind=kind,  # type: ignore[arg-type]
    )]


def _gochara_signals(day: DayContext, natal: NatalContext) -> list[Signal]:
    out: list[Signal] = []
    for planet, favourable_houses in rules.GOCHARA_FAVOURABLE_HOUSES.items():
        if planet == "Moon":
            continue  # Covered by Chandra Bala.
        transit = day.transits[planet]
        house = house_from(transit.sign, natal.moon_sign)
        good = house in favourable_houses
        suffix = "good" if good else "poor"
        sig_id = f"gochara_{planet.lower()}_{suffix}"
        if good:
            reason = f"{planet} transiting house {house} from natal Moon supports steady headway."
        else:
            reason = f"{planet} transiting house {house} from natal Moon calls for patience and clear planning."
        out.append(Signal(
            id=sig_id,
            params={"planet": planet, "house": house, "sign": transit.sign, "retrograde": transit.retrograde},
            weights=_weights_for(sig_id),
            reason=reason,
            kind="favourable" if good else "unfavourable",
            scope="standing" if planet in rules.SLOW_GRAHAS else "daily",
        ))
    return out


def _saturn_cycle_signals(day: DayContext, natal: NatalContext) -> list[Signal]:
    saturn_sign = day.transits["Saturn"].sign
    state = sade_sati_state(natal.moon_sign, saturn_sign)
    if state is None:
        return []
    house = house_from(saturn_sign, natal.moon_sign)
    id_map = {
        "rising": ("sade_sati_rising", "Sade Sati rising phase (Saturn in 12th from Moon): long-term pacing and reflection."),
        "peak": ("sade_sati_peak", "Sade Sati peak phase (Saturn over natal Moon): steady discipline over haste."),
        "setting": ("sade_sati_setting", "Sade Sati setting phase (Saturn in 2nd from Moon): consolidating commitments."),
        "ashtama": ("ashtama_shani", "Ashtama Shani (Saturn in 8th from Moon): patience and careful preparation."),
        "kantaka": ("kantaka_shani", "Kantaka Shani (Saturn in 4th from Moon): balancing home and work responsibilities."),
    }
    sig_id, reason = id_map[state]
    return [Signal(
        id=sig_id,
        params={"phase": state, "saturn_sign": saturn_sign, "house": house},
        weights=_weights_for(sig_id),
        reason=reason,
        kind="theme",
        scope="standing",
    )]


def _lord_tone(lord: str, natal: NatalContext) -> tuple[float, dict[str, Any]]:
    details = (natal.planet_details or {}).get(lord)
    if not details:
        return 0.0, {"dignity": None, "house": None}
    dignity = details.get("dignity")
    house = details.get("house")
    tone = rules.DASHA_DIGNITY_TONE.get(dignity, 0.0) + rules.DASHA_HOUSE_TONE.get(house, 0.0)
    return tone, {"dignity": dignity, "house": house}


def _dasha_signals(natal: NatalContext) -> list[Signal]:
    if not natal.running_dasha:
        return []
    maha = natal.running_dasha["mahadasha"]
    antar = natal.running_dasha["antardasha"]
    maha_tone, maha_meta = _lord_tone(maha, natal)
    antar_tone, antar_meta = _lord_tone(antar, natal)
    combined_tone = 0.6 * maha_tone + 0.4 * antar_tone

    base = _weights_for("dasha_base")
    dasha_weights: dict[str, float] = {}
    for area, val in base.items():
        # Shift gently by combined_tone and keep bounded within [-0.5, 0.5] (inside [-2, 2]).
        adjusted = val + combined_tone
        dasha_weights[area] = round(max(-0.5, min(0.5, adjusted)), 4)

    sig_id = f"dasha_{maha.lower()}_{antar.lower()}"
    return [Signal(
        id=sig_id,
        params={
            "mahadasha": maha,
            "antardasha": antar,
            "maha_dignity": maha_meta["dignity"],
            "maha_house": maha_meta["house"],
            "antar_dignity": antar_meta["dignity"],
            "antar_house": antar_meta["house"],
        },
        weights=dasha_weights,
        reason=f"Running {maha} mahadasha and {antar} antardasha shapes the broader period theme.",
        kind="theme",
        scope="standing",
    )]


def _panchang_signals(day: DayContext) -> list[Signal]:
    out: list[Signal] = []
    panchang = day.panchang
    tithi = panchang["tithi"]
    tithi_num = int(tithi.number)
    paksha = tithi.extra.get("paksha", "shukla")

    if tithi_num == rules.AMAVASYA_TITHI_NUMBER:
        out.append(Signal(
            id="amavasya",
            params={"tithi_number": tithi_num, "tithi_name": tithi.en},
            weights=_weights_for("amavasya"),
            reason="Amavasya tithi favours quiet review and closure rather than major new starts.",
            kind="unfavourable",
        ))
    elif (tithi_num % 15) in rules.RIKTA_PAKSHA_TITHIS:
        out.append(Signal(
            id="rikta_tithi",
            params={"tithi_number": tithi_num, "tithi_name": tithi.en, "paksha": paksha},
            weights=_weights_for("rikta_tithi"),
            reason=f"Rikta tithi ({tithi.en}) suggests completing existing work before launching new plans.",
            kind="unfavourable",
        ))

    karana = panchang["karana"]
    if karana.en == rules.VISHTI_KARANA_EN:
        out.append(Signal(
            id="vishti_karana",
            params={"karana": karana.en},
            weights=_weights_for("vishti_karana"),
            reason="Vishti (Bhadra) karana at sunrise favours routine follow-up over fresh commitments.",
            kind="unfavourable",
        ))

    yoga = panchang["yoga"]
    if yoga.en in rules.INAUSPICIOUS_YOGAS:
        out.append(Signal(
            id="inauspicious_yoga",
            params={"yoga": yoga.en, "yoga_number": int(yoga.number)},
            weights=_weights_for("inauspicious_yoga"),
            reason=f"{yoga.en} yoga calls for extra care with scheduling and details.",
            kind="unfavourable",
        ))

    vara_en = panchang["vara"][0]
    lord = rules.VARA_LORDS[vara_en]
    out.append(Signal(
        id=f"vara_{vara_en.lower()}",
        params={"vara": vara_en, "lord": lord},
        weights=_weights_for("neutral"),
        reason=f"{vara_en} is ruled by {lord}.",
        kind="info",
    ))

    mercury = day.transits["Mercury"]
    if mercury.retrograde:
        out.append(Signal(
            id="mercury_retrograde",
            params={"sign": mercury.sign},
            weights=_weights_for("neutral"),
            reason="Mercury is retrograde: double-check messages, travel details, and schedules.",
            kind="info",
        ))

    return out


def _coming_up_signals(day: DayContext, natal: NatalContext | None) -> list[Signal]:
    sunrise = day.panchang["sunrise"]
    earliest = None
    for key in rules.COMING_UP_GRAHAS:
        ing = next_ingress(key, after=sunrise, within_days=rules.COMING_UP_WINDOW_DAYS)
        if ing is not None and (earliest is None or ing.when < earliest.when):
            earliest = ing
    if earliest is None:
        return []

    to_sign_name = zodiac.SIGNS[earliest.to_sign - 1][0]
    new_house = house_from(earliest.to_sign, natal.moon_sign) if natal is not None else None
    house_note = f" (house {new_house} from natal Moon)" if new_house is not None else ""
    return [Signal(
        id=f"coming_up_{earliest.key.lower()}_ingress",
        params={
            "planet": earliest.key,
            "from_sign": earliest.from_sign,
            "to_sign": earliest.to_sign,
            "when": earliest.when.isoformat(),
            "house": new_house,
        },
        weights=_weights_for("neutral"),
        reason=f"Coming up: {earliest.key} enters {to_sign_name}{house_note} on {earliest.when.date().isoformat()}.",
        kind="coming_up",
    )]


def evaluate_signals(day: DayContext, natal: NatalContext | None) -> list[Signal]:
    """Evaluate all applicable horoscope rule families for ``day`` and optional ``natal``."""
    signals: list[Signal] = []
    if natal is not None:
        signals.extend(_chandra_bala_signals(day, natal))
        signals.extend(_tara_bala_signals(day, natal))
        signals.extend(_gochara_signals(day, natal))
        signals.extend(_saturn_cycle_signals(day, natal))
        signals.extend(_dasha_signals(natal))
    signals.extend(_panchang_signals(day))
    signals.extend(_coming_up_signals(day, natal))
    return signals
