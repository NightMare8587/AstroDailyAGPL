"""Which content keys still lack wording."""
from .keys import LANGS, REQUIRED_KEYS
from .lint import SnippetData


def coverage_gaps(snippets: list[SnippetData], *, statuses: tuple[str, ...] = ("draft", "reviewed"),
                  min_variants: int = 1) -> list[tuple[str, str, int]]:
    """(key, lang, count) for every required key and language with fewer than ``min_variants`` snippets."""
    have: dict[tuple[str, str], int] = {}
    for s in snippets:
        if s.status in statuses:
            have[(s.signal, s.lang)] = have.get((s.signal, s.lang), 0) + 1
    return [(k, lang, have.get((k, lang), 0)) for k in REQUIRED_KEYS for lang in LANGS
            if have.get((k, lang), 0) < min_variants]
