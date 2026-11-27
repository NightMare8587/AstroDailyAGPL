# AstroDaily

A Vedic astrology app for India: more than a kundli generator. It gives each user a daily
horoscope, daily do/don't guidance with muhurat, home-screen widgets and notifications, and
an AI layer for personalised 1-to-1 guidance built from the user's birth details and
computed chart data. There is no human astrologer in the loop.

**Status:** planning. No code yet. See [docs/architecture.md](docs/architecture.md) and
[docs/base-information.md](docs/base-information.md).

## Plan in one paragraph

All calculation runs on the server (Python, FastAPI, Swiss Ephemeris, Lahiri ayanamsa). A
Flutter app (Android and iOS) reads cached results through an API. A rule engine produces the
daily horoscope and do/don't from the chart, the running dasha, transits and the day's
panchang. An LLM is used only for 1-to-1 chat, and only on top of already-computed data. It
never calculates positions.

## Licence

This repository is licensed under the **GNU Affero General Public License v3.0** (see
[LICENSE](LICENSE)). The calculation engine depends on Swiss Ephemeris, which is dual-licensed
(AGPL or a paid Professional licence). We chose the AGPL option, so this code is open source,
including when run as a network service.

Not part of this repository: the astrologer-written horoscope copy, the curated knowledge
base and the AI prompts live in a separate private repository.
