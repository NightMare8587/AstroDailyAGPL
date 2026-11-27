"""Automatic checks every snippet must pass before it can be imported. Pure functions, no database."""
import re
from dataclasses import dataclass

from .keys import ALL_SLOTS, KINDS, LANGS, SLOTS, STATUSES, slots_in

MAX_CHARS = 160
MIN_CHARS = 12

# Calm and practical, never frightening, never overclaiming (see docs/content-draft-v0.md).
BANNED_EN = re.compile(
    r"\b(death|die|dies|dying|disease|illness|accident|curse[sd]?|doom|fatal|disaster|"
    r"will definitely|guaranteed?|certainly will|classical|ancient)\b", re.IGNORECASE)
BANNED_HI = re.compile(r"(मृत्यु|मौत|बीमारी|रोग से|दुर्घटना|श्राप|अभिशाप|विनाश|निश्चित रूप से|गारंटी|प्राचीन|शास्त्रीय)")
_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
_LATIN = re.compile(r"[A-Za-z]")


@dataclass(frozen=True)
class SnippetData:
    signal: str
    lang: str
    kind: str
    variant: int
    text: str
    status: str = "draft"


def lint_snippet(s: SnippetData) -> list[str]:
    """Return a list of problems (empty if the snippet is fine)."""
    errs: list[str] = []
    if s.signal not in SLOTS:
        errs.append(f"unknown signal key {s.signal!r}")
    if s.lang not in LANGS:
        errs.append(f"lang must be one of {LANGS}")
    if s.kind not in KINDS:
        errs.append(f"kind must be one of {KINDS}")
    if s.status not in STATUSES:
        errs.append(f"status must be one of {STATUSES}")
    if not isinstance(s.variant, int) or s.variant < 1:
        errs.append("variant must be a positive integer")
    text = s.text.strip() if isinstance(s.text, str) else ""
    if not text:
        return errs + ["text is empty"]
    if len(text) < MIN_CHARS:
        errs.append(f"text shorter than {MIN_CHARS} characters")
    if len(text) > MAX_CHARS:
        errs.append(f"text longer than {MAX_CHARS} characters ({len(text)})")
    if text != s.text:
        errs.append("text has leading or trailing whitespace")
    if "  " in text:
        errs.append("text has a double space")
    # Slot syntax: braces must pair up as {name} and name must be allowed for this signal.
    stripped = re.sub(r"\{\w+\}", "", text)
    if "{" in stripped or "}" in stripped:
        errs.append("malformed slot braces")
    allowed = SLOTS.get(s.signal, frozenset())
    for slot in slots_in(text):
        if slot not in ALL_SLOTS:
            errs.append(f"unknown slot {{{slot}}}")
        elif slot not in allowed:
            errs.append(f"slot {{{slot}}} is not available for {s.signal}")
    if BANNED_EN.search(text) or BANNED_HI.search(text):
        errs.append("contains a banned word or phrase")
    prose = re.sub(r"\{\w+\}", "", text)
    if s.lang == "hi" and not _DEVANAGARI.search(prose):
        errs.append("Hindi text has no Devanagari")
    if s.lang == "en" and _DEVANAGARI.search(prose):
        errs.append("English text contains Devanagari")
    if s.lang == "hi" and len(_LATIN.findall(prose)) > 0:
        errs.append("Hindi text contains Latin letters")
    return errs


def lint_set(snippets: list[SnippetData]) -> list[str]:
    """Lint a whole set: each snippet, plus uniqueness of (signal, lang, kind, variant) and of the text."""
    out: list[str] = []
    seen_key: dict[tuple, int] = {}
    seen_text: dict[tuple, str] = {}
    for i, s in enumerate(snippets):
        label = f"{s.signal}/{s.lang}/v{s.variant}"
        out += [f"{label}: {e}" for e in lint_snippet(s)]
        key = (s.signal, s.lang, s.kind, s.variant)
        if key in seen_key:
            out.append(f"{label}: duplicate variant number")
        seen_key[key] = i
        tkey = (s.lang, s.text.strip().lower())
        if tkey in seen_text and seen_text[tkey] != label:
            out.append(f"{label}: same text as {seen_text[tkey]}")
        seen_text.setdefault(tkey, label)
    return out
