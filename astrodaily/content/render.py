"""Fill a snippet's {slots} from a signal's params, in the requested language."""
import re
from typing import Any

from ..calc import names, zodiac

_SLOT = re.compile(r"\{(\w+)\}")


def _idx(lang: str) -> int:
    return 1 if lang == "hi" else 0


def _planet(value: Any, lang: str) -> str | None:
    pair = zodiac.PLANET_NAMES.get(str(value).title())
    return pair[_idx(lang)] if pair else None


def _sign(value: Any, lang: str) -> str | None:
    """Params carry a sign as a number or an English name."""
    try:
        n = int(value)
        return zodiac.SIGNS[n - 1][_idx(lang)] if 1 <= n <= 12 else None
    except (TypeError, ValueError):
        pass
    for en, hi in zodiac.SIGNS:
        if en == value:
            return (en, hi)[_idx(lang)]
    return None


def _nakshatra(value: Any, lang: str) -> str | None:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return names.NAKSHATRA[n - 1][_idx(lang)] if 1 <= n <= 27 else None


def _yoga(params: dict[str, Any], lang: str) -> str | None:
    n = params.get("yoga_number")
    return names.YOGA[int(n) - 1][_idx(lang)] if isinstance(n, int) and 1 <= n <= 27 else None


def _tithi_name(params: dict[str, Any], lang: str) -> str | None:
    n = params.get("tithi_number")
    if not isinstance(n, int) or not 1 <= n <= 30:
        return None
    if n == 15:
        return names.PURNIMA[_idx(lang)]
    if n == 30:
        return names.AMAVASYA[_idx(lang)]
    return names.TITHI[(n - 1) % 15][_idx(lang)]


def _paksha(params: dict[str, Any]) -> str | None:
    if params.get("paksha"):
        return str(params["paksha"])
    n = params.get("tithi_number")
    return ("shukla" if n <= 15 else "krishna") if isinstance(n, int) and 1 <= n <= 30 else None


def _vara(value: Any, lang: str) -> str | None:
    for en, hi in names.VARA:
        if en.lower() == str(value).lower():
            return (en, hi)[_idx(lang)]
    return None


def slot_values(params: dict[str, Any], lang: str) -> dict[str, str]:
    """Every slot we can resolve for this signal. Slots without a value are simply absent."""
    vals: dict[str, str | None] = {
        "nakshatra": _nakshatra(params.get("nakshatra"), lang),
        "yoga": _yoga(params, lang),
        "tithi_name": _tithi_name(params, lang),
        "paksha": (names.PAKSHA.get(_paksha(params), (None, None))[_idx(lang)]),
        "vara": _vara(params.get("vara"), lang),
        "lord": _planet(params.get("lord"), lang),
        "planet": _planet(params.get("planet"), lang),
        "mahadasha": _planet(params.get("mahadasha"), lang),
        "antardasha": _planet(params.get("antardasha"), lang),
        "sign": _sign(params.get("sign"), lang),
        "moon_sign": _sign(params.get("moon_sign"), lang),
        "saturn_sign": _sign(params.get("saturn_sign"), lang),
        "to_sign": _sign(params.get("to_sign"), lang),
        "from_sign": _sign(params.get("from_sign"), lang),
        "house": str(params["house"]) if params.get("house") is not None else None,
        "karana": None,
        "tara_name": params.get("tara_name"),
        "when": str(params["when"]) if params.get("when") is not None else None,
    }
    if lang == "en":
        vals["karana"] = params.get("karana")
    return {k: v for k, v in vals.items() if v}


def fill(text: str, params: dict[str, Any], lang: str) -> str | None:
    """The text with slots filled, or None when a slot cannot be resolved (caller falls back)."""
    values = slot_values(params, lang)
    missing = False

    def repl(m: re.Match) -> str:
        nonlocal missing
        v = values.get(m.group(1))
        if v is None:
            missing = True
            return ""
        return v

    out = _SLOT.sub(repl, text)
    return None if missing else out
