"""Build the daily push text from a card. Kept short and free of birth details: lock screens are public."""
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .sender import Push

TITLE = {"en": "Your day ahead", "hi": "आपका आज का दिन"}
BEST = {"en": "Best time", "hi": "शुभ समय"}
MAX_BODY = 140


def _clock(value: datetime, tz: str) -> str:
    return value.astimezone(ZoneInfo(tz)).strftime("%H:%M")


def daily_push(card: dict[str, Any], lang: str, with_window: bool = True) -> Push:
    """card: a localized card dict (``dos`` lines carry ``text`` and ``reason``)."""
    tz = card["location"]["timezone"]
    first = card["dos"][0] if card["dos"] else None
    headline = (first.get("text") or first.get("reason")) if first else None
    parts = [headline] if headline else []
    best = card["windows"]["best"] if with_window else []  # the times are for paying users
    if best:
        parts.append(f"{BEST[lang]} {_clock(best[0]['start'], tz)}-{_clock(best[0]['end'], tz)}")
    body = " ".join(parts) or TITLE[lang]
    if len(body) > MAX_BODY:
        body = body[: MAX_BODY - 1].rstrip() + "…"
    return Push(title=TITLE[lang], body=body,
                data={"type": "daily", "date": card["date"].isoformat(), "score": str(card["score"])})
