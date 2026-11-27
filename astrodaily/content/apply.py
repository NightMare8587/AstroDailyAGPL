"""Add library wording to a card without touching the cached core."""
from typing import Any

from .catalog import Catalog

_LISTS = ("dos", "donts", "why")
_SINGLE = ("theme", "coming_up")


def _with_text(sig: dict[str, Any], catalog: Catalog, lang: str, seed: str) -> dict[str, Any]:
    line = catalog.pick(sig["id"], sig["params"], lang, seed)
    if line is None and lang != "en":
        line = catalog.pick(sig["id"], sig["params"], "en", seed)
    return {**sig, "text": line.text if line else None, "text_lang": line.lang if line else None}


def localize(card: dict[str, Any], catalog: Catalog, lang: str, seed: str) -> tuple[dict[str, Any], bool]:
    """Return (card with ``text``/``text_lang`` on every signal, fully_in_requested_language).

    A signal with no snippet keeps ``text`` None and the client shows ``reason`` (engine English).
    The flag is true only when every shown suggestion came from the library in the requested language.
    """
    out = dict(card)
    for name in _LISTS:
        out[name] = [_with_text(s, catalog, lang, seed) for s in card[name]]
    for name in _SINGLE:
        out[name] = _with_text(card[name], catalog, lang, seed) if card[name] else None
    shown = out["dos"] + out["donts"] + ([out["theme"]] if out["theme"] else [])
    in_lang = bool(shown) and all(s["text_lang"] == lang for s in shown)
    return out, in_lang
