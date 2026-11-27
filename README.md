# AstroDaily

A Vedic astrology app for India: more than a kundli generator. It gives each user a daily
horoscope, daily do/don't guidance with muhurat, home-screen widgets and notifications, and
an AI layer for personalised 1-to-1 guidance built from the user's birth details and
computed chart data. There is no human astrologer in the loop.

**Status:** early backend. Working: `GET /v1/panchang` (tithi, nakshatra, yoga, karana, rahu kaal,
gulika, yamaganda, abhijit, choghadiya; English and Hindi), Google sign-in, sessions, and accounts
on Postgres, birth-place search over GeoNames (India), and the kundli (birth chart and Vimshottari
dasha), saved birth profiles, and daily horoscope cards (rules only, English wording). Not built yet: the
content library (proper English and Hindi text), AI chat, notifications. See [docs/architecture.md](docs/architecture.md) and
[docs/base-information.md](docs/base-information.md).

## Plan in one paragraph

All calculation runs on the server (Python, FastAPI, Swiss Ephemeris, Lahiri ayanamsa). A
Flutter app (Android and iOS) reads cached results through an API. A rule engine produces the
daily horoscope and do/don't from the chart, the running dasha, transits and the day's
panchang. An LLM is used only for 1-to-1 chat, and only on top of already-computed data. It
never calculates positions.

## Run locally

```
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env            # optional; defaults work
.venv/bin/uvicorn astrodaily.main:app --reload
.venv/bin/python -m pytest
```

Accounts need Postgres: set `DATABASE_URL` and run `.venv/bin/alembic upgrade head`. Tests run on
in-memory SQLite by default; set `TEST_DATABASE_URL` to a throwaway Postgres database to run them
(and the Alembic migration) against Postgres too.

Try: `GET /v1/panchang?date=2025-11-05&lat=28.6139&lon=77.209&tz=Asia/Kolkata` and `GET /health`.

Settings come from environment variables (see `.env.example`). The Gemini model is
`GEMINI_MODEL` (default `gemini-3.5-flash-lite`), so it can be changed on Railway without a
code release. A `Dockerfile` is included for Railway.

## Auth

The Flutter app signs in with Google (`google_sign_in`) and sends the Google **ID token** to
`POST /v1/auth/google`. The backend verifies it against `GOOGLE_CLIENT_IDS`, creates or updates
the user, and returns a 15-minute access token (JWT) plus a rotating refresh token (stored only as
a SHA-256 hash). Replaying a used refresh token revokes all of that user's sessions.

| Endpoint | Purpose |
|---|---|
| `POST /v1/auth/google` | Exchange a Google ID token for session tokens |
| `POST /v1/auth/refresh` | Rotate the refresh token, get a new access token |
| `POST /v1/auth/logout` | Revoke a refresh token |
| `GET /v1/me` | Current user |
| `PATCH /v1/me` | Set `language` (`en` or `hi`), record `consent_version` |
| `DELETE /v1/me` | Permanently delete the account and its tokens |

You must create the Google OAuth client IDs yourself (Google Cloud console) and set
`GOOGLE_CLIENT_IDS` and `JWT_SECRET` on Railway. Google's signing certificates are fetched on each
login; caching them is a later optimisation.

## Kundli

`POST /v1/kundli` calculates a birth chart. Nothing is stored. Body: `date`, `time` (local),
the birth place as `place_id` (from place search) or `lat` and `lon` (+ optional `tz`), and optional
`utc_offset_minutes` (overrides the timezone), `node` (`mean` default, or `true`) and `as_of` (date for
the running dasha, default today). It returns the lagna, the nine grahas (sign, degree, nakshatra and
pada, house, retrograde, dignity, Navamsa sign), the twelve houses, and the Vimshottari dasha: balance
at birth, all nine mahadashas with their antardashas, and the mahadasha, antardasha and
pratyantardasha running on `as_of`. Names are in English and Hindi.

Conventions: sidereal, Lahiri ayanamsa; whole-sign houses (the lagna's sign is house 1); Rahu is the
mean node by default and Ketu is opposite; nodes are shown retrograde; a dasha year is 365.25 days.
`warnings` lists anything the user should confirm: births before 15 Aug 1947 (local mean time or
wartime +06:30 may apply) and local times skipped or repeated by a clock change.

Not built yet: divisional charts beyond Navamsa, bhava chalit houses, yogas, ashtakavarga, an unknown
birth time mode, and saving a birth profile on the account.

## Birth profiles

Signed-in users who have recorded consent can save birth profiles (their own and up to 5 in total, so
family charts work): `POST /v1/profiles`, `GET /v1/profiles`, `GET`, `PATCH` and `DELETE
/v1/profiles/{id}`, and `GET /v1/profiles/{id}/kundli` for the chart (query `node`, `as_of`). Consent is
recorded with `PATCH /v1/me {"consent_version": "..."}`; until then profile endpoints answer 403. Profiles
are private to their owner, deleted with the account, and exportable with `GET /v1/me/export`.
See [docs/privacy-and-data.md](docs/privacy-and-data.md).

## Daily horoscope

Rule-based cards from the engine in `astrodaily/horoscope/` (design: [docs/daily-horoscope-design.md](docs/daily-horoscope-design.md)).
A card has a day score, five area scores (career, money, relationships, health and energy, mind and
learning), up to three suggestions for and against, a background theme, a "coming up" note, best and
avoid time windows, the panchang of the day, and the list of signals behind it ("why"). Wording is the
engine's English `reason` text for now; `lang=hi` is accepted and answered honestly (`translated: false`).

| Endpoint | Who | Level |
|---|---|---|
| `GET /v1/horoscope/rashi/{1..12}?date=&place_id=&lat=&lon=&lang=` | anyone | A (Moon sign only) |
| `GET /v1/profiles/{id}/horoscope?date=&place_id=&lat=&lon=&lang=` | signed in, consent, owner | B (natal Moon, nakshatra, lagna, dasha) |
| `GET /v1/me/horoscope` | signed in, consent | B, the user's first profile |
| `GET /v1/me/horoscope/widget` | signed in, consent | a few hundred bytes for widgets and notifications |
| `POST /v1/horoscope/feedback` | signed in | thumbs up or down on a card; re-rating replaces |

Where the sky is read: an explicit place if given, else the signed-in user's home city, else (profile
cards) the birth place, else New Delhi. Cards are computed in about 6 ms and kept in a small in-process
cache; nothing is stored except feedback. The classical rule tables behind the signals are still
**unverified** (see the design doc), so treat the content as a preview.

## Places

`GET /v1/places/search?q=<start of name>&limit=10` returns matching places, biggest first, each with
name, Hindi name (when GeoNames has one), state, district, latitude, longitude and IANA timezone.
It matches English, alternate and Hindi names (`bangalore` finds Bengaluru), needs 2+ letters, and
ignores accents and case. `GET /v1/places/{id}` returns one place.
`GET /v1/panchang?date=...&place_id=<id>` uses the place's coordinates and timezone, as an
alternative to `lat` and `lon`.

**Home city.** During onboarding the app lets the user pick a home city with the place search and
saves it: `PATCH /v1/me {"home_place_id": 1273294}` (send `null` to clear it; `GET /v1/me` returns
`home_place`). A signed-in user can then call `GET /v1/panchang?date=...` with no location and the
home city is used (`location_source: "home"`). A location in the request always wins. No device
location permission is needed. An invalid token is ignored when the request carries its own
location, and answers 401 only when the home city is needed.

Load the data (GeoNames, CC BY 4.0, about 558k populated places in India, 150 MB, about 20 seconds):

```
DATABASE_URL=... .venv/bin/python -m astrodaily.tools.import_geonames --country IN
```

It is safe to re-run: places are updated in place, so users' saved home cities survive. GeoNames gives population for only about 7,400
Indian places, so villages sort alphabetically after the towns; always show state and district.
Hindi names exist for only about 1,400 places. Birth times before 1947 need care: the IANA
`Asia/Kolkata` zone knows local mean time and wartime offsets, but the app should let the user
confirm the offset.

## Rate limiting

Per client IP, sliding one-minute window, in memory: `/v1/panchang` 60, `/v1/auth/*` 10, `/v1/me` 120
requests a minute (`RATE_LIMIT_*` variables; `/health` is not limited). Over the limit the API
returns `429` with a `Retry-After` header. In production the client IP is the `X-Real-IP` header, which
Railway overwrites at its edge (checked live: forged `X-Real-IP` and `X-Forwarded-For` values are
replaced), configurable with `CLIENT_IP_HEADER`; locally it is the socket address. Counters are per process:
with more than one replica, move them to Redis. Panchang dates are limited to 1800-2200.

## Verification status

Checked against published values: Lahiri ayanamsa at J2000, Makar Sankranti 2025, and the
tithi and end times around Diwali and Kartik Purnima 2025 (Delhi). The kundli was cross-checked
against a different engine and ephemeris (`ndastro-engine`, Skyfield with JPL DE440) over 20 births
from 1945 to 2024: the seven grahas agree to within 0.006 degrees, the lagna to 0.07 degrees, the true
node to 0.08 degrees, and mahadasha start dates to within 1 to 3 days (a 0.006 degree Moon difference
moves a 20-year dasha by about 3 days). Three of those births are fixed as reference values in the tests. Rahu Kaal, Gulika and
Yamaganda use the standard weekday segment tables. The choghadiya tables were written from
memory of the published tables and are not yet checked against an independent source.

## Licence

This repository is licensed under the **GNU Affero General Public License v3.0** (see
[LICENSE](LICENSE)). The calculation engine depends on Swiss Ephemeris, which is dual-licensed
(AGPL or a paid Professional licence). We chose the AGPL option, so this code is open source,
including when run as a network service.

Not part of this repository: the astrologer-written horoscope copy, the curated knowledge
base and the AI prompts live in a separate private repository.
