"""Name-syllable hint: which Moon sign the first syllable of a first name points to.

By tradition a child's name starts with the syllable of the birth nakshatra pada: 27 nakshatras x 4 padas
= 108 syllables. Nine padas make a sign, starting at Ashwini pada 1 (Aries). So the first syllable of a
name suggests a Moon sign. It is only a HINT: many modern names are not chosen this way, the lists differ a
little between regions, and one syllable can sit in several nakshatras. We use it only to choose between the
two signs the Moon could have been in on a birth date when the birth time is unknown.

DRAFT: the table below must be checked by a Jyotish reviewer. docs/name-syllables.md lists the sources it was
compared with, the regional differences found, and what is still unverified.
"""
import re

# Per nakshatra (1..27, in order), per pada (1..4): the accepted Latin spellings of its syllable.
# More than one spelling means regional lists differ for that pada. DRAFT, see the module note.
SYLLABLES: list[list[list[str]]] = [
    [["chu"], ["che"], ["cho"], ["la"]],              # 1 Ashwini
    [["li"], ["lu"], ["le"], ["lo"]],                 # 2 Bharani
    [["a"], ["i"], ["u"], ["e"]],                     # 3 Krittika
    [["o"], ["va"], ["vi"], ["vu"]],                  # 4 Rohini
    [["ve"], ["vo"], ["ka"], ["ki"]],                 # 5 Mrigashira
    [["ku"], ["gha"], ["nga"], ["chha"]],             # 6 Ardra
    [["ke"], ["ko"], ["ha"], ["hi"]],                 # 7 Punarvasu
    [["hu"], ["he"], ["ho"], ["da"]],                 # 8 Pushya
    [["di"], ["du"], ["de"], ["do"]],                 # 9 Ashlesha
    [["ma"], ["mi"], ["mu"], ["me"]],                 # 10 Magha
    [["mo"], ["ta"], ["ti"], ["tu"]],                 # 11 Purva Phalguni
    [["te"], ["to"], ["pa"], ["pi"]],                 # 12 Uttara Phalguni
    [["pu"], ["sha"], ["na"], ["tha"]],               # 13 Hasta
    [["pe"], ["po"], ["ra"], ["ri"]],                 # 14 Chitra
    [["ru"], ["re"], ["ro"], ["ta"]],                 # 15 Swati
    [["ti"], ["tu"], ["te"], ["to"]],                 # 16 Vishakha
    [["na"], ["ni"], ["nu"], ["ne"]],                 # 17 Anuradha
    [["no"], ["ya"], ["yi"], ["yu"]],                 # 18 Jyeshtha
    [["ye"], ["yo"], ["bha"], ["bhi"]],               # 19 Mula
    [["bhu"], ["dha"], ["pha"], ["dha"]],             # 20 Purva Ashadha
    [["bhe"], ["bho"], ["ja"], ["ji"]],               # 21 Uttara Ashadha
    [["khi", "ju"], ["khu", "je"], ["khe", "jo"], ["kho", "gha"]],  # 22 Shravana (lists differ)
    [["ga"], ["gi"], ["gu"], ["ge"]],                 # 23 Dhanishta
    [["go"], ["sa"], ["si"], ["su"]],                 # 24 Shatabhisha
    [["se"], ["so"], ["da"], ["di"]],                 # 25 Purva Bhadrapada
    [["du"], ["tha"], ["jha"], ["nya", "jna"]],       # 26 Uttara Bhadrapada (pada 4 is the letter ञ)
    [["de"], ["do"], ["cha"], ["chi"]],               # 27 Revati
]


def sign_of_pada(nakshatra: int, pada: int) -> int:
    """Moon sign (1..12) of a nakshatra pada: nine padas to a sign, counting from Ashwini pada 1."""
    return ((nakshatra - 1) * 4 + (pada - 1)) // 9 + 1


def _build_index() -> dict[str, list[tuple[int, int, int]]]:
    index: dict[str, list[tuple[int, int, int]]] = {}
    for n, padas in enumerate(SYLLABLES, start=1):
        for p, spellings in enumerate(padas, start=1):
            for sp in spellings:
                index.setdefault(sp, []).append((n, p, sign_of_pada(n, p)))
    return index


INDEX = _build_index()
_BY_LENGTH = sorted(INDEX, key=len, reverse=True)

# --- turning a typed name into Latin letters ---------------------------------------------------------

_DEV_VOWELS = {"अ": "a", "आ": "a", "इ": "i", "ई": "i", "उ": "u", "ऊ": "u", "ए": "e", "ऐ": "e", "ओ": "o", "औ": "o",
               "ऋ": "ri"}
_DEV_MATRAS = {"ा": "a", "ि": "i", "ी": "i", "ु": "u", "ू": "u", "े": "e", "ै": "e", "ो": "o", "ौ": "o", "ृ": "ri"}
_DEV_CONS = {"क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ng", "च": "ch", "छ": "chh", "ज": "j", "झ": "jh",
             "ञ": "ny", "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n", "त": "t", "थ": "th", "द": "d",
             "ध": "dh", "न": "n", "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m", "य": "y", "र": "r",
             "ल": "l", "व": "v", "श": "sh", "ष": "sh", "स": "s", "ह": "h"}
_VIRAMA, _NUKTA = "्", "़"


def _from_devanagari(text: str) -> str:
    out: list[str] = []
    chars = [c for c in text if c != _NUKTA]
    for i, c in enumerate(chars):
        nxt = chars[i + 1] if i + 1 < len(chars) else ""
        if c in _DEV_VOWELS:
            out.append(_DEV_VOWELS[c])
        elif c in _DEV_CONS:
            out.append(_DEV_CONS[c])
            if nxt not in _DEV_MATRAS and nxt != _VIRAMA:
                out.append("a")  # the inherent vowel
        elif c in _DEV_MATRAS:
            out.append(_DEV_MATRAS[c])
        # the virama, nasal marks and anything else add no letters
    return "".join(out)


def to_latin(name: str) -> str:
    """Lowercase Latin letters only, with long vowels folded to short (aa -> a, ee -> i, oo -> u)."""
    text = _from_devanagari(name) if re.search("[ऀ-ॿ]", name) else name
    text = re.sub(r"[^a-z]", "", text.lower())
    for long, short in (("aa", "a"), ("ee", "i"), ("ii", "i"), ("oo", "u"), ("uu", "u")):
        text = text.replace(long, short)
    return text


def first_syllable(name: str) -> str | None:
    """The longest table syllable that the name starts with, or None when it starts with none of them."""
    latin = to_latin(name.strip().split()[0] if name.strip() else "")
    for syl in _BY_LENGTH:
        if latin.startswith(syl):
            return syl
    return None


def hint(name: str | None, candidates: list[int]) -> dict | None:
    """Which of the candidate Moon signs the name's first syllable points to.

    Returns {"syllable", "sign", "nakshatra", "pada"} only when exactly one candidate fits, else None
    (the name does not start with a table syllable, fits neither sign, or fits both)."""
    syl = first_syllable(name or "")
    if syl is None:
        return None
    fits = [(n, p, s) for n, p, s in INDEX[syl] if s in candidates]
    signs = {s for _, _, s in fits}
    if len(signs) != 1:
        return None
    n, p, s = fits[0]
    return {"syllable": syl, "sign": s, "nakshatra": n, "pada": p}
