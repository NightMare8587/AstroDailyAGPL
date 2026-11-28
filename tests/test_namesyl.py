import pytest

from astrodaily.calc import namesyl
from astrodaily.calc.names import NAKSHATRA


def test_the_table_is_27_nakshatras_of_4_padas_and_every_pada_has_a_syllable():
    assert len(namesyl.SYLLABLES) == 27 == len(NAKSHATRA)
    for n, padas in enumerate(namesyl.SYLLABLES, start=1):
        assert len(padas) == 4, n
        for spellings in padas:
            assert spellings and all(s.isalpha() and s == s.lower() for s in spellings)


@pytest.mark.parametrize("nak,pada,sign", [
    (1, 1, 1), (1, 4, 1), (2, 4, 1), (3, 1, 1),      # Aries: Ashwini, Bharani, Krittika pada 1
    (3, 2, 2), (4, 4, 2), (5, 2, 2),                  # Taurus: Krittika 2-4, Rohini, Mrigashira 1-2
    (5, 3, 3),                                        # Gemini starts at Mrigashira pada 3
    (8, 1, 4), (13, 1, 6), (17, 2, 8), (27, 4, 12),   # Pushya is in Cancer; Hasta pada 1 in Virgo; Anuradha in Scorpio
])
def test_pada_to_sign_nine_padas_to_a_sign(nak, pada, sign):
    assert namesyl.sign_of_pada(nak, pada) == sign


def test_every_sign_owns_exactly_nine_padas():
    from collections import Counter
    counts = Counter(namesyl.sign_of_pada(n, p) for n in range(1, 28) for p in range(1, 5))
    assert counts == {s: 9 for s in range(1, 13)}


@pytest.mark.parametrize("name,syllable", [
    ("Asha", "a"), ("Aarav", "a"), ("Pulkit", "pu"), ("Chandra", "cha"), ("Hari", "ha"), ("Ravi", "ra"),
    ("Mohan", "mo"), ("Bhavna", "bha"), ("  asha verma", "a"),
])
def test_first_syllable_from_a_latin_name(name, syllable):
    assert namesyl.first_syllable(name) == syllable


@pytest.mark.parametrize("name,syllable", [("आशा", "a"), ("पुलकित", "pu"), ("चंद्र", "cha"), ("हरि", "ha"), ("मोहन", "mo")])
def test_first_syllable_from_a_devanagari_name(name, syllable):
    assert namesyl.first_syllable(name) == syllable


def test_a_name_that_starts_with_no_table_syllable_gives_no_hint():
    assert namesyl.first_syllable("Xavier") is None
    assert namesyl.first_syllable("") is None
    assert namesyl.hint("Xavier", [1, 2]) is None
    assert namesyl.hint(None, [1, 2]) is None


def test_hint_picks_the_candidate_sign_the_syllable_belongs_to():
    # "A" is Krittika pada 1, which is in Aries.
    assert namesyl.hint("Asha", [1, 2]) == {"syllable": "a", "sign": 1, "nakshatra": 3, "pada": 1}
    # "Pu" is Hasta pada 1, in Virgo, whichever side it is on.
    assert namesyl.hint("Pulkit", [5, 6])["sign"] == 6
    assert namesyl.hint("Pulkit", [6, 7])["sign"] == 6


def test_hint_is_none_when_the_syllable_fits_neither_sign():
    assert namesyl.hint("Pulkit", [1, 2]) is None


def test_hint_is_none_when_it_fits_both_signs():
    # "Ta" sits in Purva Phalguni pada 2 (Leo) and Swati pada 4 (Libra): candidates Leo and Libra both fit.
    assert {s for _, _, s in namesyl.INDEX["ta"]} >= {5, 7}
    assert namesyl.hint("Tara", [5, 7]) is None


# The 108 syllables as published by the sources listed in docs/name-syllables.md (Drik Panchang and AstroSage lists,
# cross-checked with Prokerala, MyPanchang and Wikipedia). Every one of them must be in our table. Our table may hold
# extra regional spellings for a pada, never fewer.
PUBLISHED = [
    "chu che cho la", "li lu le lo", "a i u e", "o va vi vu", "ve vo ka ki", "ku gha nga chha", "ke ko ha hi",
    "hu he ho da", "di du de do", "ma mi mu me", "mo ta ti tu", "te to pa pi", "pu sha na tha", "pe po ra ri",
    "ru re ro ta", "ti tu te to", "na ni nu ne", "no ya yi yu", "ye yo bha bhi", "bhu dha pha dha",
    "bhe bho ja ji", "khi khu khe kho", "ga gi gu ge", "go sa si su", "se so da di", "du tha jha jna", "de do cha chi",
]


def test_every_published_syllable_is_in_our_table():
    for n, row in enumerate(PUBLISHED, start=1):
        for pada, syl in enumerate(row.split(), start=1):
            ours = namesyl.SYLLABLES[n - 1][pada - 1]
            assert syl in ours or (n == 26 and pada == 4 and "nya" in ours), (NAKSHATRA[n - 1][0], pada, syl, ours)


def test_the_extra_spellings_are_only_the_known_regional_ones():
    extras = {(n, p): [x for x in namesyl.SYLLABLES[n - 1][p - 1] if x not in PUBLISHED[n - 1].split()[p - 1:p]]
              for n in range(1, 28) for p in range(1, 5)}
    assert {k: v for k, v in extras.items() if v} == {
        (22, 1): ["ju"], (22, 2): ["je"], (22, 3): ["jo"], (22, 4): ["gha"],  # Shravana: the 27-star (South) list
        (26, 4): ["nya"],                                                       # the letter ञ
    }


def test_devanagari_nya_letter():
    assert namesyl.to_latin("ञ") == "nya"


def test_hint_with_devanagari_multi_word_and_odd_input():
    assert namesyl.hint("आशा वर्मा", [1, 2])["sign"] == 1          # only the first word counts
    assert namesyl.hint("  asha-verma ", [1, 2])["sign"] == 1
    assert namesyl.first_syllable("1234") is None
    assert namesyl.first_syllable("---") is None
    assert namesyl.hint("Asha", []) is None
