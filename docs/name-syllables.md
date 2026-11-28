# Name syllables and the Moon sign

Status: DRAFT, 2026-11-28. Needs a Jyotish reviewer before real users rely on it.

## What it is for

The setup page asks for date, time and place of birth. With a birth time the Moon sign (janma rashi) is calculated
exactly. When the person does not know the time, the Moon changed sign during the birth date on about 44% of dates,
so there are two possible signs. The first syllable of the first name is then used as a **hint** to pre-select one of
the two. The person always confirms. Code: `astrodaily/calc/namesyl.py`, `moonsign.py`, `POST /v1/moon-sign`.

## How the hint works

1. Take the first word of the first name (Latin or Devanagari) and fold it to lowercase Latin letters
   (`aa` to `a`, `ee` to `i`, `oo` to `u`).
2. Find the longest syllable from the 108-syllable table that the name starts with (`pulkit` starts with `pu`).
3. A syllable belongs to a nakshatra pada. Nine padas make a sign, counting from Ashwini pada 1 (Aries):
   `sign = ((nakshatra - 1) * 4 + (pada - 1)) // 9 + 1`.
4. A syllable can sit in more than one nakshatra (`ta` is in Purva Phalguni and Swati). Only the signs that are also
   possible on the birth date count. If exactly one sign remains, that sign is suggested; if none or both remain, there
   is no suggestion.

It is a hint only. Many modern names are not chosen from the birth nakshatra, and a name that starts with none of the
108 syllables (for example `Krishna`, whose first sound is a consonant cluster) gives no hint.

## Janma rashi and naam rashi

The janma rashi is the Moon's sidereal sign at birth and is the standard basis for a birth chart, dasha and transits.
The naam rashi is the sign of the name's first syllable; it is used when birth details are unknown, and in newspaper
daily horoscopes. AstroDaily's daily card uses the janma rashi. The name only helps choose between two signs.

## The table and where it comes from

The table was checked against Drik Panchang and AstroSage (the two lists agree), cross-checked with Prokerala,
MyPanchang and Wikipedia, by an Antigravity research run on 2026-11-28. The test `test_every_published_syllable_is_in_our_table`
holds the published list; our table may add regional spellings, never drop one.

Sources (as reported by the research run):

- https://www.drikpanchang.com/baby-names/name-initials.html
- https://www.drikpanchang.com/rashiphal/find-rashi-with-name.html
- https://www.astrosage.com/nakshatra/ and https://www.astrosage.com/baby-names/
- https://www.prokerala.com/astrology/baby-names/
- https://www.mypanchang.com/nakshatranames.php
- https://en.wikipedia.org/wiki/List_of_Nakshatras
- https://www.jansatta.com/horoscope/know-difference-between-birth-rashi-and-name-rashi/1083072/ (janma vs naam rashi)

## Differences between sources, and what we did

| Place | Variants | Choice |
|---|---|---|
| Shravana (all 4 padas) | North: khi khu khe kho. South (27-star): ju je jo gha | Both kept (all are Capricorn) |
| Uttara Bhadrapada pada 4 | the letter ञ: nya, jna | `nya` and `jna` (not `na`, which belongs to Hasta and Anuradha) |
| Retroflex and dental pairs (Ashlesha di/du/de/do, Purva Phalguni ta/ti/tu, Uttara Phalguni te/to, Hasta sha/na, Vishakha) | spelled with ट/त, ड/द, ष/श, ण/न | Treated as the same Latin letter |
| Short and long vowels (chu/chū, hu/hū, ru/rū, mu/mū) | spelling only | One Latin spelling |
| Rohini, Mrigashira, Mula (va/ba, ve/be, bha/ba) | some lists swap v and b | Not kept: the primary lists use v and bha. A name starting `Ba` gives no hint from these |
| Ardra pada 2 and 3 | gha or kha; nga, na or da | Primary only (gha, nga) |
| Purva Ashadha pada 3 and 4 | pha and dha, or bha and pha | Primary only (pha, dha) |
| Vishakha pada 2 and 3 | some lists swap tu and te | Primary order (tu, te); the sign is the same either way |

## Not verified (for the reviewer)

- The research run reported that its web access returned search summaries, not the raw pages, and that it could not
  open a printed source such as Muhurta Chintamani. The table matches what the portals publish, but nobody has compared
  it against a printed text.
- Whether the Shravana South list should be kept or dropped for North Indian users.
- Whether `v` and `b` lists (Rohini, Mrigashira) should be added for names such as Bhavna or Bunty.
- The Devanagari reader handles the first letters of ordinary names only (no conjunct clusters such as क्र).
