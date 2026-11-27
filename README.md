# AstroDaily

A Vedic astrology app for India: more than a kundli generator. It gives each user a daily
horoscope, daily do/don't guidance with muhurat, home-screen widgets and notifications, and
an AI layer for personalised 1-to-1 guidance built from the user's birth details and
computed chart data. There is no human astrologer in the loop.

**Status:** backend scaffold. `GET /v1/panchang` works (tithi, nakshatra, yoga, karana, rahu kaal,
gulika, yamaganda, abhijit, choghadiya; English and Hindi). Kundli, dashas, daily horoscope and AI
chat are not built yet. See [docs/architecture.md](docs/architecture.md) and
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

Try: `GET /v1/panchang?date=2025-11-05&lat=28.6139&lon=77.209&tz=Asia/Kolkata` and `GET /health`.

Settings come from environment variables (see `.env.example`). The Gemini model is
`GEMINI_MODEL` (default `gemini-3.5-flash-lite`), so it can be changed on Railway without a
code release. A `Dockerfile` is included for Railway.

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
