"""Which content keys the engine can need, and which slots each key may use.

A snippet is written for a *content key*: usually the signal id, except the dasha family, which has one
key (``dasha``) because the running period changes the slots, not the sentence.
"""
import re

LANGS = ("en", "hi")
KINDS = ("line",)
STATUSES = ("draft", "reviewed", "retired")

_PLANETS = ("sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu", "ketu")
_NAKSHATRA_CATS = ("dhruva", "chara", "kshipra", "mridu", "ugra", "tikshna", "mishra")
_TARAS = ("janma", "sampat", "vipat", "kshema", "pratyak", "sadhana", "naidhana", "mitra", "parama_mitra")
_VARAS = ("sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday")

# key -> slots the engine fills for it (every slot must be in the signal's params or resolvable).
SLOTS: dict[str, frozenset[str]] = {}


def _add(keys, slots):
    for k in keys:
        SLOTS[k] = frozenset(slots)


_add([f"nakshatra_{c}" for c in _NAKSHATRA_CATS], {"nakshatra"})
_add(["tithi_nanda", "tithi_bhadra", "tithi_jaya", "tithi_purna", "rikta_tithi", "amavasya"],
     {"tithi_name", "paksha"})
_add([f"vara_{v}" for v in _VARAS], {"vara", "lord"})
_add(["special_ekadashi", "special_pradosh", "special_sankashti", "special_purnima"], set())
_add(["inauspicious_yoga"], {"yoga"})
_add(["vishti_karana"], set())  # always Vishti, so no slot
_add(["chandra_bala_good", "chandra_bala_poor"], {"house", "moon_sign"})
_add([f"tara_{t}" for t in _TARAS], {"nakshatra", "tara_name"})
_add([f"gochara_{p}_{q}" for p in _PLANETS if p != "moon" for q in ("good", "poor")],
     {"planet", "house", "sign"})
_add(["sade_sati_rising", "sade_sati_peak", "sade_sati_setting", "ashtama_shani", "ardhashtama_shani"], {"house", "saturn_sign"})
_add(["mercury_retrograde"], {"sign"})
_add(["dasha"], {"mahadasha", "antardasha"})
_add(["coming_up_saturn_ingress", "coming_up_jupiter_ingress", "coming_up_rahu_ingress"],
     {"planet", "house", "to_sign", "from_sign", "when"})

REQUIRED_KEYS: tuple[str, ...] = tuple(sorted(SLOTS))
ALL_SLOTS: frozenset[str] = frozenset().union(*SLOTS.values())

_SLOT_RE = re.compile(r"\{(\w*)\}")


def key_for(signal_id: str) -> str:
    """Content key for an engine signal id."""
    return "dasha" if signal_id.startswith("dasha_") else signal_id


def slots_in(text: str) -> list[str]:
    return _SLOT_RE.findall(text)
