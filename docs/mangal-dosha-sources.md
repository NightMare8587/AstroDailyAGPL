# Mangal (Kuja) dosha: sources and what is and is not verified

Written 2026-11-28 from a check by a separate agent that read the texts (no chat context). The app follows ONE rule, below.

## The rule the app uses
**Brihat Parashara Hora Shastra 80.47** (Sanskrit-edition numbering): Mars in the 1st, 12th, 4th, 7th or 8th house from the Lagna,
without the aspect or conjunction of a benefic, is the dosha. `calc/yogas.py` counts houses 1, 4, 7, 8, 12 from the Lagna and
treats Jupiter or Venus joining or aspecting Mars as removing it. The verse does not name the benefics; Jupiter and Venus are
our choice. Read from the Lagna only, as the verse is. Not applied: the mutual cancellation when both partners have it
(BPHS 80.49), which belongs to matching.

Verified by reading: BPHS Chapter 80 verses 47, 48, 49 (vedicpupil.in; Santhanam's English translation, archive.org
BPHSEnglish, whose OCR drops "1st" from the English of v. 47, while the Sanskrit has "lagne").

## Other documented traditions (not applied)
- **Jataka Parijata 14.34** (Vaidyanatha Dikshita): the Sanskrit names Mars in the 2nd, 12th, 7th, 4th and 8th as harmful to the
  wife (read at vedicpupil.in; Sastri's English OCR only shows the 7th, 4th and 8th, and numbers the verse 35).
- **B. V. Raman, Muhurtha (marriage chapter) and How to Judge a Horoscope vol. II (7th house):** houses 2, 12, 4, 7 and 8 (the 1st
  is not in his list), reckoned from the Lagna, the Moon and Venus (weak from the Lagna, stronger from the Moon, strongest from
  Venus). Exempt signs: 2nd Gemini/Virgo; 12th Taurus/Libra; 4th Aries/Scorpio; 7th Capricorn/Cancer; 8th Sagittarius/Pisces;
  Leo and Aquarius none. Cancelled by Mars with Jupiter or with the Moon, by Jupiter or Venus in the ascendant, and when both
  partners have it. He attributes the stanza only to "the Kerala Sastra" (no book named) and says much importance need not be
  given to it. (ved.bz/_jyotish/books/muhurtha.html; archive.org how-to-judge-a-horoscope.)

## Claims found in research notes that are NOT verified (do not use)
Muhurta Chintamani verse 50/51 as the source of the house list or the sign-house exemptions (a secondary book credits those verses
to Muhurta Sangraha Darpana, Agastya Samhita and Muhurta Parijata); Jyotirnibandha as a source; the Raman quotation "hardly a
horoscope without this dosha"; Raman page numbers; BPHS chapter 34 per-lagna verse numbers (Scorpio is 35-36 and says only that
Mars is neutral); any rule that Mars as lagna lord, an own or exalted sign, Jupiter's signs in every house, or age 28 cancels it.
One secondary book quotes a Muhurta Chintamani line saying own, exalted or friend's-sign Mars cancels it; nobody has read it in
Muhurta Chintamani itself, so it is not used.

## For the reviewer
Decide which tradition the app should follow, whether to add the Moon and Venus charts, and the cancellations above. The verse is
about a woman's chart; verse 48 extends it to a man's.
