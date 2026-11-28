# Compatibility (Ashtakoota)

`GET /v1/me/match/{profile_id}` matches the signed-in person's own profile with another profile they saved. It needs
consent and a birth time for both people (without: 409; yourself: 422; someone else's profile: 404). Nothing is stored:
the match is worked out from the two Moon positions on each request, with no model involved.

## The eight parts (36 points)

Varna 1, Vashya 2, Tara 3, Yoni 4, Graha Maitri 5, Gana 6, Bhakoot 7, Nadi 8 (`calc/matching.py`). The response has the
total, a gentle band (`great` 33+, `good` 25+, `fair` 18+, `low`; no band tells anyone not to marry), and for each part
its points, what it looks at and what each person has (a group, an animal, a planet, a sign or a birth star), in English
and Hindi (`content/match_text.py`).

## Who is who

Varna, Vashya, Gana and Yoni depend on the order. The signed-in person is the first column of the tables (the groom
column in the books) and the other person the second; `?swap=true` puts the other person first. Each person in the answer
carries `is_you`.

## Written summary

`GET /v1/me/match/{profile_id}/summary?lang=&swap=` is a short model-written paragraph (strengths, one or two things to talk
through, one small suggestion). The model gets only the numbers (Moon signs, birth stars, the eight scores, who is the first
column): no names and no birth details, and the prompt forbids verdicts about marrying and any fixed fate. It is built once
per ordered pair and language and kept in `match_summaries`; it is cleared when either person's birth details change, goes
with either profile or the account, and is in the export.

## What is verified, and what is not

These are common published rules, not reviewed by a Jyotish expert (the response carries the usual disclaimer).
The Yoni matrix, the Gana table, Graha Maitri and Nadi were checked against all 11,664 boy and girl birth star and pada
pairs of an open-source reference and agree exactly. They disagree on purpose in places where sources differ:

- **Varna:** Taurus, Virgo and Capricorn are Vaishya and Gemini, Libra and Aquarius are Shudra (the reference has them
  the other way round).
- **Vashya:** the table and the Sagittarius and Capricorn halves follow a widely repeated one; sources disagree and the
  orientation of the table is the least certain part.
- **Tara:** counted both ways in nines, 3 / 1.5 points (the reference scores it differently).
- **Bhakoot:** Cancer with Aquarius is 8th and 6th, so 0 points (one pair in the reference says 7).
