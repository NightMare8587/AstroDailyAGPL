# AstroDaily

A Vedic astrology app for India: more than a kundli generator. It gives each user a daily
horoscope, daily do/don't guidance with muhurat, home-screen widgets and notifications, and
an AI layer for personalised 1-to-1 guidance built from the user's birth details and
computed chart data. There is no human astrologer in the loop.

**Status:** early backend. Working: `GET /v1/panchang` (tithi, nakshatra, yoga, karana, rahu kaal,
gulika, yamaganda, abhijit, choghadiya; English and Hindi), Google sign-in, sessions, and accounts
on Postgres. Not built yet: place search, kundli, dashas, daily horoscope, AI chat. See [docs/architecture.md](docs/architecture.md) and
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

## Rate limiting

Per client IP, sliding one-minute window, in memory: `/v1/panchang` 60, `/v1/auth/*` 10, `/v1/me` 120
requests a minute (`RATE_LIMIT_*` variables; `/health` is not limited). Over the limit the API
returns `429` with a `Retry-After` header. Behind Railway's proxy the client IP is the last
`X-Forwarded-For` entry (`TRUSTED_PROXY_HOPS`, default 1 in production). Counters are per process:
with more than one replica, move them to Redis. Panchang dates are limited to 1800-2200.

## Verification status

Checked against published values: Lahiri ayanamsa at J2000, Makar Sankranti 2025, and the
tithi and end times around Diwali and Kartik Purnima 2025 (Delhi). Rahu Kaal, Gulika and
Yamaganda use the standard weekday segment tables. The choghadiya tables were written from
memory of the published tables and are not yet checked against an independent source.

## Licence

This repository is licensed under the **GNU Affero General Public License v3.0** (see
[LICENSE](LICENSE)). The calculation engine depends on Swiss Ephemeris, which is dual-licensed
(AGPL or a paid Professional licence). We chose the AGPL option, so this code is open source,
including when run as a network service.

Not part of this repository: the astrologer-written horoscope copy, the curated knowledge
base and the AI prompts live in a separate private repository.
