# Daily horoscope and do/don't: design

Status: draft v0.1 (2026-11-27). Design only, no code yet. Items marked **Open** need a decision from
the product owner. Classical rule tables below are written from standard Jyotish practice and are
**UNVERIFIED** until checked against the public-domain Sanskrit sources (see section 9).

## Build status (2026-11-27)

**Phase 1 (pure engine) is built and committed**: transits and ingresses, the rule families, centred
scoring, daily-first selection, muhurat windows and a deterministic day report, in `astrodaily/calc/transits.py`
and `astrodaily/horoscope/`. Written by Antigravity and reviewed by Claude. 123 tests pass. It is **not**
reachable from the API yet, and all rule tables are still **unverified** (section 9).

What the first measurement taught us, and what changed from the sections below:

- **Heavy slow-planet weights make a bad card.** Over a year and all 12 Moon signs, the first version scored
  45% of days a 2, none a 1 or 5, and repeated the same "avoid" items on 97% of consecutive days. Fixes: signals
  carry a `scope` (`daily` or `standing`); the do and don't lists are filled from daily signals first; every rule
  family is centred so its long-run expected contribution is zero and the average day scores 3.
- **Level A needs rules that change daily.** The day's nakshatra category (Dhruva, Chara, Kshipra, Mridu, Ugra,
  Tikshna, Mishra) and tithi category (Nanda, Bhadra, Jaya, Purna, Rikta, Amavasya) are now rule families. They
  cut repetition of the "do" items from 84% to 11% and of the "avoid" items from 58% to 40% on Level A.
- **A float comparison dropped the last daytime choghadiya slot on 43% of days.** Fixed and tested.
- Acceptance is measured by a script (score balance and list repetition across 12 Moon signs and a year); a
  version of it should move into the repository's tests or CI.

Known weak points: area scoring detects some rule families by signal-id prefix (brittle); the one-sided rules
(Vishti karana, inauspicious yogas, Saturn cycles) are corrected by an offset, not by a partition; Abhijit
Muhurat is treated as valid every weekday, which some sources dispute; the "coming up" ingress search is redone
on every call.

## 1. Goal

Every day, each user gets guidance that is personal to their chart, explains itself, and fits a
home-screen widget and a notification:

- a day score and a one-line headline;
- scores for a few life areas;
- three things to do and three to avoid, today;
- the best and the worst time windows (muhurat);
- a short "why": the astrological signals behind it.

There is no human astrologer writing each day. So the system is built to be **deterministic first**:
rules decide what is true about the day, a reviewed content library says it in words, and an LLM is an
optional last step that may reword but never decide.

## 2. Principles

1. **Rules decide, words describe.** All astrology (what is favourable, why) comes from computed data
   and a rule table. The LLM never calculates and never adds astrological claims.
2. **Every card shows its reasons.** Each statement links to the signals that caused it. This builds
   trust and makes bugs findable.
3. **Cheap by default.** The free path costs almost nothing per user: calculation is milliseconds, text
   comes from a stored library, results are cached per day.
4. **Original content only.** No copied horoscope text. Method (rules) is not copyrightable; prose is.
5. **Gentle, not frightening.** Guidance is framed as habits and timing, never as predictions of illness,
   death, loss or catastrophe. No medical, legal or financial advice. A visible note that it is for
   reflection.
6. **Reproducible.** The same user and date give the same card unless the rules or content version
   changed. Every card records the engine and content versions used.

## 3. Two levels of personalisation

| Level | Needs | Based on | Unique cards a day |
|---|---|---|---|
| **A. Rashi** (Moon sign) | Nothing, works signed out | The 12 Moon signs vs today's transits and panchang | 12 |
| **B. Personal** | A saved birth profile | Natal Moon sign and nakshatra, lagna and houses, the running dasha and antardasha, plus level A | 1 per profile |

Indian daily horoscopes are by Moon sign, so level A matches what users expect and is the widget
default. Level B is the differentiator: it adds nakshatra-based Tara Bala, the dasha, and house
placements. Level A is cached for everyone; level B is computed per profile on first request and cached.

## 4. Inputs (what we compute)

Existing: panchang for the day and place (tithi, nakshatra, yoga, karana, rahu kaal, gulika, yamaganda,
abhijit, choghadiya), the natal chart, the dasha periods.

New calculation module `calc/transits.py`:
- positions of the nine grahas at the day's sunrise for the user's place (sidereal, Lahiri);
- each graha's house **counted from the natal Moon** (gochara) and from the lagna (level B);
- retrograde status, and whether a graha changes sign within the next 30 days (for "coming up" notes);
- Saturn's Sade Sati and Ashtama Shani state for the natal Moon.

Day definition: the user's **local calendar date**, with the panchang taken at that day's sunrise.
Timezone and place come from the profile (level B) or the home place (level A with a rashi).
**Open:** sunrise-to-sunrise (traditional) versus midnight-to-midnight. Default: sunrise.

## 5. Rule engine

### 5.1 Signals

A **signal** is a small fact with a weight per life area, produced by a rule. Examples:

`chandra_bala_good(house=6)`, `tara_vipat`, `gochara_saturn_unfavourable(house=12)`,
`sade_sati(phase=peak)`, `vishti_karana`, `rikta_tithi`, `dasha_period(maha=Saturn, antar=Venus)`,
`mercury_retrograde`, `abhijit_available`.

### 5.2 Rule families (all UNVERIFIED tables; see section 9)

| Family | Rule | Level |
|---|---|---|
| **Chandra Bala** | Today's Moon in houses 1, 3, 6, 7, 10, 11 from the natal Moon is favourable | A, B |
| **Tara Bala** | Count from the birth nakshatra to today's nakshatra, modulo 9: Janma, Sampat, Vipat, Kshema, Pratyak, Sadhana, Naidhana, Mitra, Parama Mitra. Vipat, Pratyak, Naidhana are unfavourable. | B |
| **Gochara** | Each graha's house from the natal Moon vs its traditional favourable houses (Sun 3,6,10,11; Moon 1,3,6,7,10,11; Mars 3,6,11; Mercury 2,4,6,8,10,11; Jupiter 2,5,7,9,11; Venus 1,2,3,4,5,8,9,11,12; Saturn 3,6,11; Rahu and Ketu to be confirmed). Slow planets weigh more than fast ones. | A, B |
| **Saturn cycles** | Sade Sati (Saturn in the 12th, 1st, 2nd from natal Moon), Ashtama Shani (8th), Kantaka (4th): a standing background theme, not a daily alarm | A, B |
| **Dasha** | The running mahadasha and antardasha lords set the **theme** of the period, and their natal house and dignity set its tone | B |
| **Day quality (panchang)** | Weekday lord, rikta tithis (4, 9, 14), Amavasya, Vishti karana (Bhadra), inauspicious yogas, nakshatra type | A, B |

### 5.3 Scoring

Areas (**Open**, default five): **Career, Money, Relationships, Health and energy, Mind and learning.**

1. Each signal adds a weight (positive or negative) to each area it concerns, from a rule table kept in
   data, not code, so it can be tuned.
2. Sum per area, then map to a 1-5 score with fixed thresholds. The overall day score is a weighted mean.
3. Weights are deliberately small and bounded so no single signal swings the whole card, and so the
   day never reads as all-bad. Even a hard day has a "what helps" angle.
4. The mapping is a data file with a version number. Changing it is a content release, not a code change.

### 5.4 Muhurat windows (do/don't timing)

- **Best windows:** the highest-ranked choghadiya slots (Amrit, Shubh, Labh, Char) and Abhijit, minus any
  overlap with Rahu Kaal, Gulika and Yamaganda, at least 45 minutes long. Return the top two.
- **Avoid windows:** Rahu Kaal, plus Kaal and Rog choghadiya slots that fall in daytime.
- All computed from the panchang we already have; nothing new to source.

### 5.5 Selection

Out of all signals, choose what to say:
- the 3 strongest favourable and the 3 strongest unfavourable (by weight);
- one "background theme" (dasha or Saturn cycle);
- at most one "coming up" item (a sign change in the next 30 days).
Ties break by freshness: prefer signals not shown to this user recently.

## 6. Content library

### 6.1 Shape

A snippet is: `signal id`, `language` (en, hi), `kind` (headline, do, dont, why, theme, area note),
`area`, `variant` number, `text`, `status` (draft, reviewed, retired), `version`.
Texts use named slots such as `{time_window}`, `{house}`, `{planet}`, filled by the engine.
Several variants per snippet (aim for 4) and a deterministic rotation by user and date avoid a daily
card that reads the same.

### 6.2 Where it lives

Private content repository, as decided earlier. It is imported into a Postgres table
(`content_snippets`) by an import tool, like the GeoNames importer, so the public AGPL repo and the
Railway build never need the content, and content updates do not need a code deploy.

### 6.3 How it is written without an astrologer (**Open: who reviews**)

1. **Draft** with Gemini, from a brief per signal that states the rule and the tone guide, offline and
   in batches. The model writes sentences; it does not choose astrology.
2. **Lint** automatically: banned words (death, disease, accident, curse, doom, "will definitely"),
   length limits, slot syntax, English and Hindi both present for every snippet, no duplicate text.
3. **Review** by a human: a person who knows Jyotish for the meaning, and a native Hindi reader for the
   Hindi. Nothing reaches users with status `draft`.
4. **Coverage check** in CI: every signal the engine can emit has reviewed snippets in both languages.

Size estimate: about 60 signal types x 4 variants x 3 kinds x 2 languages, roughly 1,500 short snippets.
Reviewing them is the main human effort in this feature.

### 6.4 Tone guide (to be written with the owner)

Warm, practical, second person, present tense. Suggest, do not command. Say "a good day to finish pending
work", not "you will succeed". Avoid fear and avoid certainty. Short sentences that fit a widget.

## 7. Optional LLM layer ("polish")

Off by default for the free path. When on, the model receives only the chosen signals and snippets as
JSON and rewrites them into one short, natural paragraph in the user's language. Rules:
- it may not add, remove or reorder astrological claims (checked by comparing the claims it was given);
- the structured card is always returned alongside, so the app can fall back to it;
- cached per (profile, date, language), so a repeated open costs nothing;
- model name is configuration (`GEMINI_MODEL`); a paid key only, never the free tier, because the free
  tier may use data to improve Google's products and the input is derived from birth details.

Rough cost, one call about 600 input and 250 output tokens at the Flash-Lite price on 2026-11-27
($0.30 and $2.50 per million): about $0.0008 a call. 1,000 daily users: about $24 a month. 10,000: about
$240 a month. This is an estimate, not a measurement.

## 8. API, storage, jobs

### 8.1 Endpoints

| Endpoint | Auth | Purpose |
|---|---|---|
| `GET /v1/horoscope/rashi/{1..12}?date=&lang=` | none | Level A card |
| `GET /v1/profiles/{id}/horoscope?date=&lang=` | user + consent | Level B card |
| `GET /v1/me/horoscope?date=&lang=` | user + consent | The user's first profile, for the app home and widgets |
| `GET /v1/me/horoscope/widget` | user + consent | Small payload: headline, score, best window |
| `POST /v1/horoscope/feedback` | user | Thumbs up or down, and "felt accurate", on a card |

Card shape: `date`, `location`, `score`, `headline`, `areas` (score and short note each), `dos[3]`,
`donts[3]`, `windows` (best and avoid, with times), `theme`, `why[]` (signals, readable), `language`,
`generated_by` (`rules` or `rules+llm`), `engine_version`, `content_version`.

### 8.2 Storage

- `content_snippets`: the library above.
- `horoscope_cache`: key (kind, rashi or profile id, local date, language), JSON payload, versions.
  Cache is rebuilt when versions change. Level A is shared; level B rows belong to the profile and are
  deleted with it (deletion and export rules from `privacy-and-data.md` apply).
- `horoscope_feedback`: user id, card key, rating, time. Deleted with the account.

### 8.3 Jobs

First version is **lazy and cached**: compute on first request, store, serve. Level A can be pre-filled
by a nightly job. Notifications later need a scheduled job (a second Railway service on a cron) that
precomputes the next day for users who turned notifications on. **Open:** notification time of day.

### 8.4 Widgets and notifications

The widget endpoint returns a few hundred bytes so the phone can refresh in the background. A
notification carries the headline and best window, and opens the full card.

## 9. Verification plan (we cannot trust tables from memory)

1. **Rule tables:** have Antigravity (or Codex, per the routing rules) compile Chandra Bala, Tara Bala
   and gochara tables from the public-domain Sanskrit texts (Brihat Parashara Hora Shastra,
   Phaladeepika, Brihat Samhita) with chapter and verse citations, and flag disagreements between
   sources. A person who knows Jyotish signs off. Avoid copyrighted modern translations.
2. **Ingress dates as test vectors:** known sidereal ingresses, which we can assert in tests once the
   transit module exists: Saturn from Aquarius to Pisces on 29 March 2025, Jupiter into Gemini on
   14 May 2025, Rahu into Aquarius on 18 May 2025. These are recalled, not yet checked; confirm each
   against an independent engine before using it.
3. **Cross-check** transits against the independent JPL-based engine already used for the kundli.
4. **Golden days:** a set of fixed (profile, date) pairs whose signals are written down by hand and
   asserted in tests, so a rule change shows up as a failing test.
5. **Live check after every deploy**, the same way as for the kundli.

There is no ground truth for "is this horoscope right". We measure other things: rules are
implemented as documented, content is reviewed, users rate cards, and we never claim accuracy.

## 10. Build phases

1. **Transits and signals (pure code).** `calc/transits.py`, the rule families, scoring, windows,
   selection. Tested with ingress vectors and golden days. No database.
2. **Content pipeline.** Snippet schema, importer, lint and coverage check, the Gemini drafting script,
   a handful of reviewed snippets to prove the loop. Needs the reviewer decision.
3. **API and cache.** Endpoints, cache table, migration, widget payload.
4. **Polish and loop.** Optional LLM layer, feedback endpoint, notification job, weight tuning from
   feedback.

Phases 1 and 3 are code I can build now. Phase 2 is gated on who reviews the text.

## 11. Open decisions

1. **Who reviews the content**, English and Hindi, and how the first reviewed set is produced.
2. **Free versus paid.** Proposed default: levels A and B are free for one profile; LLM polish and
   extra profiles may be paid later. This is a product choice.
3. **Areas** shown on the card (default five) and the **tone**.
4. **Day boundary**: sunrise (traditional, the default) or midnight.
5. **Notification time**, and whether the first release includes notifications at all.
6. **How predictive** the language may be. Default: habits and timing only, no event predictions.

## 12. Risks

- **Content volume and quality** is the real cost, not the code.
- **Repetition:** a deterministic engine can feel stale; variants and the optional polish step mitigate it.
- **Hindi quality** of machine drafts needs a native reviewer.
- **Rule disagreement** between Jyotish traditions: we must pick one set and say so.
- **Trust and harm:** fear-based or health-related claims; mitigated by the tone guide and lint.
- **Regulation:** astrology services and advertising claims are regulated in places; get advice before
  marketing any specific claim.
