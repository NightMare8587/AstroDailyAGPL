# Architecture

Status: draft v0.1 (2026-11-27). Decisions are marked **Decided** or **Open**.

## 1. Product scope

- Daily horoscope per user, based on their own chart (not just the sun sign).
- Daily do/don't suggestions with muhurat: rahu kaal, gulika, yamaganda, abhijit, choghadiya, hora.
- Panchang: tithi, nakshatra, yoga, karana, vara, sunrise and sunset, festivals and vrats.
- Kundli: birth chart, dashas (Vimshottari first), transits (gochara).
- Flutter app with home-screen widgets and push notifications.
- AI 1-to-1 guidance from birth data and computed chart data. No human astrologer.
- Languages: English and Hindi, both at launch. **Decided**

## 2. Principles

1. **Everything is calculated server-side. Decided.** The app never computes positions.
2. **The LLM never calculates.** Positions, dashas and timings come from the deterministic
   engine as JSON. The LLM only explains and personalises that JSON.
3. **Cache aggressively.** The panchang depends on date and place only, so it is computed once
   per day per location grid cell and shared by all users. Widgets and notifications read cache.
4. **Keep cost near zero for the free path.** The daily feed is rule and template based. LLM
   spend happens only in 1-to-1 chat and has a daily limit.
5. **Keep the licence boundary clean.** Open calculation code and private content stay in
   separate repositories (section 8).

## 3. Components

```
Flutter app (Android, iOS)
   |  HTTPS (JSON)
   v
FastAPI service  -- Railway
   |-- Calc engine (Python, pyswisseph, Lahiri)   -> chart, dasha, transits, panchang, muhurat
   |-- Place and timezone (GeoNames, timezonefinder, IANA tzdb)
   |-- Daily feed generator (rules + content templates)
   |-- AI service (chart JSON + RAG -> LLM)
   |-- Notification scheduler
   v
Postgres (users, birth data, charts, cached results)      Redis (panchang cache, rate limits)
```

| Component | Decision | Notes |
|---|---|---|
| Backend language | Python 3, FastAPI. **Decided** | Best Vedic ecosystem; `pyswisseph` ships Linux wheels. |
| Ephemeris | Swiss Ephemeris via `pyswisseph`, AGPL option. **Decided** | Moshier mode needs no data files; add `.se1` files for full precision. |
| Hosting | Railway. **Decided** | One API service, Postgres, optional Redis, a cron service. |
| Database | Postgres, SQLAlchemy 2 and Alembic migrations. **Decided, built** (users, refresh tokens) | Users, birth details, stored charts, cached daily output. Relational data with JSONB for chart blobs. |
| Cache | Postgres only at first. **Decided** | Cached panchang and daily output live in Postgres tables keyed by date and location cell. Add Redis later if load needs it. |
| Mobile | Flutter. **Decided** | Widgets and notifications are the retention driver. |
| LLM | Gemini, default `gemini-3.5-flash-lite`. **Decided** | Model name is backend configuration (env var `GEMINI_MODEL`), never hard-coded, so it can be switched without a release. Alternatives in base-information section 6. |
| Auth | Google Sign-In for now. **Decided, built** | App sends Google ID token; backend issues its own access JWT (15 min) and rotating refresh token (60 days, hashed in DB). Phone OTP can be added later. |
| Push | **Open** | FCM for Android; APNs for iOS. |

## 4. Calculation engine

- Sidereal zodiac, Lahiri ayanamsa by default.
- Swiss Ephemeris for planet positions and sunrise and sunset.
- Own clean implementation of the Vedic logic on top: tithi (Moon minus Sun in 12 degree steps),
  nakshatra (Moon longitude over 13 degrees 20 minutes), yoga, karana, rahu kaal, gulika,
  yamaganda (weekday segments of the day), abhijit, choghadiya, hora, Vimshottari dasha.
- Use MIT or Apache code (`jyotisha`, `tithi_engine`) and AGPL code (PyJHora) only as a reference
  to cross-check outputs, then verify against an established source (a one-month hosted API
  trial, or Drik-style published panchang values).
- Festivals and vrats are computed from panchang rules and reviewed by a pandit for tricky
  cases (Ekadashi, Adhik Maas). Do not use Calendarific: its terms limit caching to 30 days and
  forbid ML training use.
- Never scrape Drik Panchang. It publishes no API and states copyright over its data.

## 5. Birth place and time

- GeoNames (CC-BY 4.0) imported into our own database. Search by place name.
- `timezonefinder` plus the IANA tz database for the offset.
- Google Places is not used for stored coordinates: its terms allow caching coordinates for at
  most 30 days. Place IDs can be stored, coordinates cannot.
- Births before 1947 need care: local mean time before 1906, wartime IST (+06:30) in 1941-42 and
  1942-45. Show the assumed offset and let the user correct it.

## 6. Daily horoscope and do/don't

1. Compute the user's natal chart once and store it.
2. Each day, combine natal Moon and lagna, running dasha, current transits and the day's panchang.
3. A rule engine maps these to tagged outcomes (for example "Moon transiting 8th: avoid new
   commitments").
4. Astrologer-written English and Hindi templates, kept in the private content repo, render the
   text. No LLM is needed for this path.
5. The same output feeds the feed screen, widgets and notifications.

## 7. AI 1-to-1 guidance

- Input to the LLM: the stored chart, current dasha, today's transits and panchang as JSON, and
  retrieved passages from vetted sources.
- Vetted sources only: our own authored knowledge base, public-domain root texts (BPHS,
  Phaladeepika, Jataka Parijata in Sanskrit), and datasets with clear licences.
- Avoid modern English or Hindi translations of the classics unless the licence is cleared
  (R. Santhanam's BPHS is in copyright).
- Free tier has a daily message limit; caching and shorter context keep cost down.
- The model must state that guidance is for reflection, not medical, legal or financial advice.

## 8. Repositories and licensing

| Repo | Visibility | Licence | Contents |
|---|---|---|---|
| AstroDailyAGPL (this repo) | Public | AGPL-3.0 | Calc engine, API, app code |
| Content repo (to create) | Private | All rights reserved | Horoscope copy (EN/HI), knowledge base, prompts |
| Flutter app repo (to create) | Private | All rights reserved | Mobile app. Talks to the API over HTTPS only; no Swiss Ephemeris code inside. |

Swiss Ephemeris is used under its AGPL option. That obliges the whole project that uses it to be
AGPL, including when served over a network. If the app earns money later, the CHF 700 Professional
licence (6 years, then renewal) can be bought to close new versions; already published AGPL
versions stay open. The Professional licence also forbids selling calculation as an API to other
businesses. This is a summary, not legal advice.

## 9. Cost notes (2026-11-27, indicative)

- Swiss Ephemeris: CHF 0 under AGPL.
- GeoNames, IANA tzdb, `timezonefinder`: free.
- Hosting: Railway; check current pricing before committing.
- LLM: the main running cost. Needs a fresh estimate once a model is chosen.
- Hosted astrology APIs are optional. Prokerala's free tier is 5,000 credits a month, paid from
  Rs 999 a month. Use one only to cross-check our calculations.

## 10. Open questions

1. Monthly LLM budget and the free-tier daily message limit.
2. Legal opinion on the AGPL server and private app boundary before launch (the Professional
   contract treats an app that requests calculations from a server as containing Swiss Ephemeris).
3. Privacy: retention period for inactive accounts, the consent text, and the third-party and
   region questions. Drafted in [privacy-and-data.md](privacy-and-data.md); needs your decision and
   a lawyer's review before launch.
