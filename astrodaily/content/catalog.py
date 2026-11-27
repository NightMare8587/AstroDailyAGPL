"""In-memory view of the snippet table: pick one wording per signal, deterministically."""
import time
import zlib
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from .keys import key_for
from .render import fill

TTL_SECONDS = 300


@dataclass(frozen=True)
class Line:
    text: str
    lang: str
    status: str
    version: str


class Catalog:
    def __init__(self, rows: list[tuple[str, str, int, str, str, str]]):
        """rows: (signal_key, lang, variant, text, status, version)."""
        self._by: dict[tuple[str, str], list[tuple[int, str, str, str]]] = defaultdict(list)
        for key, lang, variant, text, status, version in rows:
            self._by[(key, lang)].append((variant, text, status, version))
        for v in self._by.values():
            v.sort()

    def variants(self, key: str, lang: str) -> list[tuple[int, str, str, str]]:
        return self._by.get((key, lang), [])

    def pick(self, signal_id: str, params: dict[str, Any], lang: str, seed: str) -> Line | None:
        """One filled line in ``lang`` or None. The variant rotates with the seed (user/date), so the same
        card always reads the same, but different days and people read differently."""
        variants = self.variants(key_for(signal_id), lang)
        if not variants:
            return None
        start = zlib.crc32(f"{seed}|{signal_id}".encode()) % len(variants)
        for step in range(len(variants)):  # skip a variant whose slots cannot be filled
            _, text, status, version = variants[(start + step) % len(variants)]
            filled = fill(text, params, lang)
            if filled:
                return Line(filled, lang, status, version)
        return None


EMPTY = Catalog([])
_cache: tuple[float, Catalog] | None = None


def load_catalog(db: Session) -> Catalog:
    from ..models import ContentSnippet
    allowed = ["reviewed"] + (["draft"] if get_settings().content_allow_draft else [])
    rows = db.execute(
        select(ContentSnippet.signal_key, ContentSnippet.lang, ContentSnippet.variant,
               ContentSnippet.text, ContentSnippet.status, ContentSnippet.version)
        .where(ContentSnippet.status.in_(allowed), ContentSnippet.kind == "line")
    ).all()
    return Catalog([tuple(r) for r in rows])


def get_catalog(db: Session | None) -> Catalog:
    """The shared catalog, refreshed every few minutes. No database means no content (engine wording)."""
    global _cache
    if db is None:
        return EMPTY
    now = time.monotonic()
    if _cache is None or now - _cache[0] > TTL_SECONDS:
        try:
            _cache = (now, load_catalog(db))
        except Exception:  # content must never take a card down
            return _cache[1] if _cache else EMPTY
    return _cache[1]


def reset() -> None:
    global _cache
    _cache = None
