"""Normalise place names for prefix search: lowercase, strip diacritics, collapse punctuation, and treat
equivalent Devanagari spellings as one.

Hindi has several spellings for the same sound, and people type any of them:
  * chandrabindu and anusvara:           गुड़गाँव = गुड़गांव,  रांची = राँची
  * a nasal consonant + virama = anusvara: इन्दौर = इंदौर,  मुम्बई = मुंबई,  तिरुवनन्तपुरम = तिरुवनंतपुरम
  * the nukta (the dot under ड़, ज़):     गुड़गांव = गुडगांव  (many keyboards skip it)
Both the stored names and the query go through this function, so they always meet in the middle.
"""
import re
import unicodedata

_SPACE = re.compile(r"[\s\-_.,'’/()]+")
_NUKTA = "़"
_CHANDRABINDU, _ANUSVARA = "ँ", "ं"
_ZERO_WIDTH = re.compile("[‌‍]")
# ङ ञ ण न म + virama, before a consonant, is written as an anusvara in everyday Hindi.
_NASAL_CONJUNCT = re.compile("[ङञणनम]्(?=[क-ह])")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    # Drop Latin combining marks (Rāvi -> Ravi) but keep Devanagari vowel signs.
    text = "".join(
        ch for ch in text
        if not (unicodedata.combining(ch) and ord(ch) < 0x0900)
    )
    text = unicodedata.normalize("NFC", text).casefold()
    text = _ZERO_WIDTH.sub("", text).replace(_NUKTA, "").replace(_CHANDRABINDU, _ANUSVARA)
    text = _NASAL_CONJUNCT.sub(_ANUSVARA, text)
    return _SPACE.sub(" ", text).strip()
