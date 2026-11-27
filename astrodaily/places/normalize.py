"""Normalise place names for prefix search: lowercase, strip diacritics, collapse punctuation.

Devanagari text is kept as is (only case-folded and whitespace-collapsed), so Hindi queries match
Hindi names directly.
"""
import re
import unicodedata

_SPACE = re.compile(r"[\s\-_.,'’/()]+")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    # Drop Latin combining marks (Rāvi -> Ravi) but keep Devanagari vowel signs and nuktas.
    text = "".join(
        ch for ch in text
        if not (unicodedata.combining(ch) and ord(ch) < 0x0900)
    )
    text = unicodedata.normalize("NFC", text).casefold()
    return _SPACE.sub(" ", text).strip()
