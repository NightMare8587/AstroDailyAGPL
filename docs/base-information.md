# Base information

Research summary as of 2026-11-27. Claims were checked against primary pages where possible.
Anything not checked is marked **UNVERIFIED**.

## 1. Engines and libraries

| Name | Licence | Notes |
|---|---|---|
| Swiss Ephemeris | AGPL-3.0 or Professional licence | Accuracy standard. Professional: CHF 700, unlimited projects, valid 6 years then renew (contract Sept 2026, updated 2026-11-09). The price page separately lists CHF 750 for licence plus CD-ROM. |
| pyswisseph | AGPL-3.0 | Python binding, v2.10.3.2. We use this. |
| PyJHora | AGPL-3.0 (version suffix unresolved) | Full Jyotish. Reference only. |
| vedic-astrology-toolkit | AGPL-3.0-or-later plus attribution terms | Reference only. |
| jyotisha (jyotisham) | MIT | Python tools for Hindu calendar and astronomy; scope not fully verified. |
| ndastro-engine | MIT | Skyfield and JPL; Lahiri and Vimshottari dasha; **no panchang yet**; alpha, one maintainer. |
| VedAstro | MIT | Whether it embeds Swiss Ephemeris is UNVERIFIED. |
| sweph (pub.dev) | AGPL-3.0 (LGPL path with Professional licence) | Dart FFI bindings only. |
| jyotish (pub.dev) | MIT, but bundles Swiss Ephemeris | The MIT licence does not cover the bundled library. |
| tithi_engine (pub.dev) | Apache-2.0 | Pure Dart, tithi only, festivals removed in v6. |

## 2. Swiss Ephemeris licence facts (from the Professional contract)

- Valid for server-side software, and for an app that gets calculations from a server (that still
  counts as containing Swiss Ephemeris).
- Providing API services to third-party businesses is excluded; each such business needs its own licence.
- Valid 6 years, then renewal or stop use.
- Cannot name Astrodienst or its authors in promotion without written permission.
- Choosing AGPL instead means placing the whole project under AGPL before any public service starts.

## 3. Hosted astrology APIs (INR, ex-GST, pages read 2026-11-27)

| Provider | Pricing | Limits |
|---|---|---|
| Prokerala (api.prokerala.com) | Free 5,000 credits a month; Ruby Rs 999 (list 1,999) for 100k credits; Emerald Rs 2,499 for 350k; Sapphire Rs 4,999 for 1M | 5 / 60 / 120 / 300 requests a minute |
| AstrologyAPI | Credit wallet; Indian suite from Rs 1,500 a month; 150 free credits on signup | Not stated |
| VedicAstroAPI | Vedic Limited Rs 1,499 for 30,000 calls; Complete from Rs 2,499 for 75,000 | 14-day trial |
| DivineAPI | Vedic Sampoorna Rs 1,499 for 100k requests; overage Rs 20 per 1,000 | 14-day trial needs a card |
| FreeAstrologyAPI | Free 500 requests a day, 1 request a second; paid from Rs 1,000 for 50,000 a month | |
| VedAstro | No pricing found on the site | |

Caching, storage and resale terms for these providers were **not read** (UNVERIFIED). Read each
provider's terms of service before relying on one.

## 4. Data sources

- **Place data:** GeoNames, CC-BY 4.0, commercial use allowed with credit. File contents of
  IN.zip and cities500 not checked (see its readme).
- **Timezones:** IANA tz database via `zoneinfo`; `timezonefinder` (MIT code, ODbL boundary data).
- **Google Maps:** coordinates may be cached for 30 days only; Place IDs can be stored forever.
  Read on the Geocoding policy page; the primary Service Specific Terms were not readable.
- **Drik Panchang:** no public API; copyright over its data. Do not scrape.
- **Calendarific:** free tier 500 calls a month, attribution required; terms forbid caching beyond
  30 days, ML training use and building derivative databases. Not suitable.

## 5. Text and datasets for the AI

- Public-domain Sanskrit root texts: BPHS, Phaladeepika, Jataka Parijata, Brihat Jataka.
- In copyright, do not use: R. Santhanam's BPHS translation (1984). Sastri's translations
  (Phaladeepika, Jataka Parijata) have an unconfirmed status; treat as restricted.
- Hugging Face datasets (licence tags as declared by uploaders, not verified):
  - OurNakshatra/ournakshatra-vedic-astrology-core: CC-BY-4.0, 602 Q&A rows.
  - AmareshHebbar/jyotish-llm-sft: Apache-2.0, 1,000,000 rows of templated synthetic data from
    random charts and 15 hand-written yoga rules, no classical text. Weak as grounding.
  - shriramjiastro/bphs-97-chapters-sanskrit-dataset: CC-BY-SA-4.0, 97 rows of chapter metadata
    and formulas, not full text. ShareAlike applies to derivatives.

## 6. LLM pricing

Gemini 2.5 Flash ($0.30 input, $2.50 output per 1M tokens) is deprecated and routes to 3.5
Flash-Lite from 2026-12-01. Listed on the pricing page: 3.5 Flash-Lite ($0.30 input, $2.50
output, $0.03 cached input), and 3.6 and 3.8 Flash ($0.75 input, $3.75 output until 2026-12-31,
then double). Choose after testing quality, and re-check prices.

## 7. Corrections to the first research pass

The first AI-generated research contained errors that were fixed above: a wrong Swiss Ephemeris
term (99 years and CHF 400 per extra developer), invented AstrologyAPI plan tiers, USD prices
for Prokerala and DivineAPI, an unfounded VedAstro price, a wrong dataset licence, and an
outdated LLM recommendation.
