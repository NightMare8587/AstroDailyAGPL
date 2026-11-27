# Rule review checklist (for a person who knows Jyotish)

Status: 2026-11-27. Nothing below has been verified against a primary text. This page lets a reviewer
check each rule in minutes and say yes, no, or "change it to this".

## What the research did and did not achieve

A research pass (Codex, read-only, browser only) tried to verify the tables against public-domain
sources. **It confirmed nothing.** The only public-domain primary edition it found was a 1925
*Muhurta Chintamani* scan (Internet Archive `in.ernet.dli.2015.105158`, marked out of copyright), but its
text layer was too corrupted to read a chapter, page or verse reliably. The other material was search
summaries and secondary pages, which it correctly refused to treat as sources of record. Its report labels
most items "modern convention", but that label is not evidence: it means "no classical citation found",
and an item may still be classical. Read each entry below as **common convention, primary text unchecked**.

A second automated pass is unlikely to do better without a readable Sanskrit edition. A human reviewer
with the texts, or a good transcription, is the realistic route.

## How to review

For each rule: is our value right, as a rule the traditions you follow would accept? If it varies by
tradition, which variant should the app use, and what should it be called in the interface? Mark each
**OK**, **CHANGE TO ...**, or **DROP**. Rules marked *editorial* are the app's own and need your opinion on
wording and tone, not on citations.

What a wrong rule costs: a rule's *weight* decides how much it moves the day's score. Slow-planet rules and
the nakshatra and tithi categories weigh most. Rules with `info` kind do not change scores.

## The rules

| # | Rule | Our value (file: `astrodaily/horoscope/rules.py` unless noted) | Variants and doubts | Question for the reviewer |
|---|---|---|---|---|
| 1 | **Chandra Bala**: transiting Moon from the natal Moon | Favourable in houses 1, 3, 6, 7, 10, 11 | Widely stated; no primary page read | Is this the set you use? |
| 2 | **Tara Bala** | Count inclusive from birth nakshatra; tara = ((count-1) mod 9)+1. Unfavourable: Vipat 3, Pratyak 5, Naidhana 7. Janma 1 is "mixed" (small caution). | Janma is often described as mixed, not simply bad. Some give Parama Mitra and Sampat special weight. | Right split of the nine? How should Janma read? |
| 3 | **Gochara**: favourable houses from the natal Moon | Sun 3,6,10,11; Moon 1,3,6,7,10,11; Mars 3,6,11; Mercury 2,4,6,8,10,11; Jupiter 2,5,7,9,11; Venus 1,2,3,4,5,8,9,11,12; Saturn 3,6,11; Rahu 3,6,10,11; Ketu 3,6,11 | Seven visible planets are the common table. **Rahu and Ketu vary** between sources. **Vedha** (obstruction) rules are a second layer that we do not apply; Sun/Saturn and Moon/Mercury are the usual non-obstructing pairs. | Rahu and Ketu sets? Should the app apply vedha, or label this "simplified"? |
| 4 | **Saturn cycles** from the natal Moon sign | Sade Sati = 12th, 1st, 2nd. Ashtama Shani = 8th. **Ardhashtama Shani = 4th** (often called Dhaiya). | The code used "Kantaka Shani" for the 4th, which is not used uniformly; renamed to *Ardhashtama* on this basis. "Kantaka" is sometimes used for Saturn in other quadrants from the Moon. | Is the 4th "Ardhashtama/Dhaiya"? Should "Kantaka" exist at all, and for which houses? |
| 5 | **Tithi groups** (per paksha) | Nanda 1,6,11; Bhadra 2,7,12; Jaya 3,8,13; Rikta 4,9,14; Purna 5,10,15; Amavasya (30) separate | The groups describe *uses*, not good or bad. We score Nanda, Bhadra, Jaya, Purna mildly positive and Rikta and Amavasya negative. | Acceptable simplification, or should scoring be activity-based? What is each group for? |
| 6 | **Nakshatra categories** | Dhruva: Rohini, U.Phalguni, U.Ashadha, U.Bhadrapada. Chara: Punarvasu, Swati, Shravana, Dhanishta, Shatabhisha. Kshipra: Ashwini, Pushya, Hasta. Mridu: Mrigashira, Chitra, Anuradha, Revati. Ugra: Bharani, Magha, P.Phalguni, P.Ashadha, P.Bhadrapada. Tikshna: Ardra, Ashlesha, Jyeshtha, Mula. Mishra: Krittika, Vishakha | Aliases: Sthira/Chala, Laghu/Maitra/Krura/Daruna/Sadharana. Some lists add Abhijit to Kshipra (28-star scheme); we use 27. | Membership correct? Keep 27-star mode? Which category names to show? |
| 7 | **Inauspicious nitya yogas** | **Now nine:** Vishkambha, Atiganda, Shula, Ganda, Vyaghata, Vajra, Vyatipata, Parigha, Vaidhriti (was seven; Vishkambha and Vajra were added) | Common panchang convention. Some sources limit Vishkambha and Parigha to part of their span. | Is the nine-yoga set right? Any partial-span rules to implement? |
| 8 | **Vishti (Bhadra) karana** | Cautionary for new work. Karana index 0 = Kimstughna, 1-56 = seven movable karanas repeating eight times, 57-59 = Shakuni, Chatushpada, Naga | The numbering is consistent with 60 half-tithis. Only the "avoid" status is a convention. | Confirm Vishti as avoid, and whether Bhadra has day or night parts that matter |
| 9 | **Rahu Kaal, Gulika, Yamaganda** (`calc/panchang.py`) | Daytime (sunrise to sunset) in 8 equal parts. Rahu 8,2,7,5,6,4,3; Gulika 7,6,5,4,3,2,1; Yamaganda 4,3,2,1,7,6,5 (Sunday first) | Daylight-relative method is the common one; fixed 06:00-18:00 is a popular simplification we do not use. | Confirm segments and the daylight method |
| 10 | **Choghadiya** (`calc/panchang.py`) | Day starts Sun..Sat: Udveg, Amrit, Rog, Labh, Shubh, Char, Kaal; cycle Udveg, Char, Labh, Amrit, Kaal, Shubh, Rog; night starts five places later and steps back two | A regional, mainly Gujarati and western Indian, convention; not pan-Indian. | Show it for all users, or only as a regional option? |
| 11 | **Abhijit Muhurat** | The 8th of 15 daytime muhurtas around solar noon | Modern sources say it is not used on **Wednesday**; no classical citation found. | Apply a Wednesday exclusion? Any other weekday? |
| 12 | **Weekday lords and suits** | Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn. `VARA_SUITS` activity tags | Lord order is standard. The activity tags are *editorial*, not from a text. | Are the suggested activities fair for each day? |
| 13 | **Special days** | Ekadashi (tithi 11, 26), Pradosh (13, 28), Sankashti Chaturthi (19), Purnima (15) | Pradosh is an *evening* observance on Trayodashi; Sankashti is Krishna Chaturthi, when the moon rises. | Wording for each; should Pradosh show only for the evening window? |

## Not classical, and not up for citation

- **Weights and score thresholds** (`horoscope/weights.py`): the app's own design, tuned so the average day scores 3.
- **Dasha tone tables** (`DASHA_DIGNITY_TONE`, `DASHA_HOUSE_TONE`): editorial heuristics for how a planet's
  natal strength colours its period. A reviewer should say whether they are reasonable, not whether they are
  classical.
- **Tone and wording**: calm, practical, never frightening, no predictions of illness, loss or death.

## Decisions that follow from the research

- Keep the tables as they are, labelled as common convention in the code (done) until a reviewer signs off.
- Product wording must not call these "classical" or "ancient". Describe the day's qualities and let the
  reviewer-approved text carry any claim.
- Tithi and nakshatra categories should read as "suited to ...", not as a plain good or bad verdict
  (affects the content library, not the scoring).
- Rahu and Ketu transit scoring is the least certain scored rule. If the reviewer cannot confirm it, lower
  its weights or drop it before launch.

## Changes applied (ruleset 0.4, 2026-11-27, from an unverified self-review, not a Jyotishi)

- Abhijit Muhurat is no longer offered as a best window on Wednesdays (the panchang endpoint still reports it).
- Rahu and Ketu gochara weights are halved, and are kept lighter than Jupiter and Saturn, until a reviewer confirms them.
- Gochara card reasons now say "simplified, no vedha". Amrit choghadiya wording names the convention as mainly western Indian.
- Product wording must not say "classical" or "ancient".
